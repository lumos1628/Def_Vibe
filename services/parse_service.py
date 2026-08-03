import time
from datetime import datetime, timezone, timedelta

from api.opendota_client import OpenDotaClient, RateLimitError
from config import Config
from repositories.match_repository import MatchRepository


class ParseService:
    def __init__(
        self,
        client: OpenDotaClient,
        match_repository: MatchRepository,
    ) -> None:
        self.client = client
        self.match_repository = match_repository

    @staticmethod
    def _is_replay_available(data: dict | None) -> bool:
        if data is None:
            return False
        start_time = data.get("start_time")
        if start_time is None:
            return True
        match_date = datetime.fromtimestamp(int(start_time), tz=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(days=Config.MAX_REPLAY_AGE_DAYS)
        return match_date >= cutoff

    def _has_replay_data(self, data: dict | None) -> bool:
        if data is None:
            return False
        return self.match_repository.has_replay_data(data)

    @staticmethod
    def _is_job_done(status_response: dict | None) -> bool:
        if status_response is None:
            return True
        state = status_response.get("state") or status_response.get("status")
        if state in ("completed", "complete", "failed", "error"):
            return True
        return False

    def _handle_rate_limit(self, exc: RateLimitError) -> None:
        print(f"\n  ⚠⚠⚠ Rate limit sostenido detectado ({exc}).")
        print(f"  Pausando {Config.RATE_LIMIT_PAUSE_SECONDS} segundos antes de continuar...")
        self.client.reset_rate_limit_count()
        time.sleep(Config.RATE_LIMIT_PAUSE_SECONDS)
        print("  Reanudando con el mismo item...")

    def _fetch_and_save(self, match_id: int) -> bool:
        try:
            data = self.client.get_match(match_id)
            if data is None:
                return False
            self.match_repository.save_match_details(match_id, data)
            return self._has_replay_data(data)
        except RateLimitError:
            raise
        except Exception as exc:
            print(f"  ✗ Error consultando match {match_id}: {exc}")
            return False

    def _enqueue_unparsed(self, match_ids: list[int]) -> tuple[int, int, int]:
        verified_with_data = 0
        queued = 0
        failed = 0

        index = 0
        while index < len(match_ids):
            match_id = match_ids[index]
            progress = f"[{index + 1}/{len(match_ids)}]"
            state = self.match_repository.get_parse_state(match_id)

            try:
                if state["data_verified"]:
                    print(f"{progress} Match {match_id} ya verificado. Revisando estado...")
                    data = self.match_repository.get_match_details(match_id)
                else:
                    print(f"{progress} Verificando match {match_id}...")
                    data = self.client.get_match(match_id)
                    if data is not None:
                        self.match_repository.save_match_details(match_id, data)
                    self.match_repository.mark_data_verified(match_id)

                if data is not None and self._has_replay_data(data):
                    self.match_repository.update_parse_status(match_id, "done")
                    verified_with_data += 1
                    print(f"  ✓ Match {match_id} ya tiene datos de replay.")
                    index += 1
                    continue

                if not self._is_replay_available(data):
                    self.match_repository.mark_parsed(match_id, has_replay_data=False, unparseable=True)
                    print(f"  → Match {match_id} es muy antiguo, no se puede parsear.")
                    index += 1
                    continue

                print(f"  → Match {match_id} sin datos. Encolando parseo...")
                job_id = self.client.request_parse(match_id)
                if job_id is None:
                    self.match_repository.update_parse_status(match_id, "pending")
                    failed += 1
                    print(f"  ✗ No se pudo encolar parseo para match {match_id}.")
                    index += 1
                    continue

                self.match_repository.mark_parse_requested(match_id, job_id)
                queued += 1
                print(f"  ✓ Match {match_id} encolado (job {job_id}).")
                index += 1

            except RateLimitError as exc:
                self._handle_rate_limit(exc)
                continue
            except Exception as exc:
                print(f"  ✗ Error procesando match {match_id}: {exc}")
                self.match_repository.update_parse_status(match_id, "pending")
                failed += 1
                index += 1

        return verified_with_data, queued, failed

    def _poll_jobs(self) -> tuple[int, int]:
        queued = self.match_repository.list_queued()
        if not queued:
            return 0, 0

        print(f"\nConsultando estado de {len(queued)} job(s) encolado(s)...")
        done = 0
        still_queued = 0

        index = 0
        while index < len(queued):
            match_id, job_id = queued[index]
            print(f"[{index + 1}/{len(queued)}] Job {job_id} (match {match_id})...")
            try:
                status = self.client.get_request_status(job_id)
                if not self._is_job_done(status):
                    self.match_repository.update_parse_status(match_id, "parsing")
                    still_queued += 1
                    print(f"  → Job aún en cola/proceso.")
                    index += 1
                    continue

                print(f"  ✓ Job terminado. Obteniendo datos del match {match_id}...")
                if self._fetch_and_save(match_id):
                    self.match_repository.update_parse_status(match_id, "done")
                    done += 1
                    print(f"  ✓ Match {match_id} guardado con datos de replay.")
                else:
                    self.match_repository.update_parse_status(match_id, "pending")
                    print(f"  → Match {match_id} no tiene datos de replay.")
                index += 1
            except RateLimitError as exc:
                self._handle_rate_limit(exc)
                continue
            except Exception as exc:
                print(f"  ✗ Error consultando job {job_id}: {exc}")
                still_queued += 1
                index += 1

        return done, still_queued

    def _fetch_done_matches(self) -> int:
        queued = self.match_repository.list_queued()
        if not queued:
            return 0

        print(f"\nReintentando obtener datos de {len(queued)} match(es) encolado(s)...")
        done = 0
        index = 0
        while index < len(queued):
            match_id, _ = queued[index]
            print(f"[{index + 1}/{len(queued)}] Reintentando match {match_id}...")
            try:
                if self._fetch_and_save(match_id):
                    self.match_repository.update_parse_status(match_id, "done")
                    done += 1
                    print(f"  ✓ Match {match_id} guardado con datos de replay.")
                else:
                    print(f"  → Match {match_id} sigue sin datos de replay.")
                index += 1
            except RateLimitError as exc:
                self._handle_rate_limit(exc)
                continue
            except Exception as exc:
                print(f"  ✗ Error consultando match {match_id}: {exc}")
                index += 1

        return done

    def parse_unparsed(self) -> tuple[int, int, int, int, int]:
        match_ids = self.match_repository.list_unparsed(limit=Config.PARSE_BATCH_SIZE)
        if not match_ids:
            print("\nNo hay partidas pendientes de parseo.")
            return 0, 0, 0, 0, 0

        print(f"\nProcesando lote de {len(match_ids)} partida(s) con OpenDota...")
        print("Fase 1: Verificación y encolado")
        verified, queued, failed = self._enqueue_unparsed(match_ids)

        total_done = verified
        still_queued = queued

        if queued > 0:
            for poll in range(1, Config.PARSE_MAX_POLLS + 1):
                print(f"\n--- Ronda de polling {poll}/{Config.PARSE_MAX_POLLS} ---")
                print(f"Esperando {Config.PARSE_POLL_INTERVAL} segundos para que OpenDota procese los jobs...")
                time.sleep(Config.PARSE_POLL_INTERVAL)

                done, still_queued = self._poll_jobs()
                total_done += done

                if still_queued == 0:
                    print("\nTodos los jobs han terminado.")
                    break

            if still_queued > 0:
                print(f"\n{still_queued} job(s) aún pendiente. Reintentando obtener datos directamente...")
                total_done += self._fetch_done_matches()
                still_queued = len(self.match_repository.list_queued())

        print(f"\nParseo finalizado:")
        print(f"  {total_done} partida(s) con datos de replay")
        print(f"  {queued} partida(s) encoladas")
        print(f"  {still_queued} partida(s) aún en cola/proceso")
        print(f"  {failed} partida(s) con error al encolar")
        return total_done, queued, still_queued, failed, len(match_ids)

    def clean_old_matches(self, days: int | None = None) -> None:
        days = days if days is not None else Config.CLEAN_OLD_MATCHES_DAYS
        print(f"\nLimpiando partidas con más de {days} días de antigüedad...")
        deleted = self.match_repository.delete_old_matches(days)
        print(f"  ✓ Se eliminaron {deleted} partida(s) antigua(s).")
