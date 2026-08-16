import csv
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from api.opendota_client import OpenDotaClient, RateLimitError
from config import Config
from repositories.match_repository import MatchRepository
from services.drive_service import DriveService


class ParseService:
    def __init__(
        self,
        client: OpenDotaClient,
        match_repository: MatchRepository,
        drive_service: DriveService | None = None,
    ) -> None:
        self.client = client
        self.match_repository = match_repository
        self.drive_service = drive_service

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

    def _check_unparsed(self, match_ids: list[int]) -> tuple[int, int, int]:
        """Modo GET-only: consulta cada partida sin encolar jobs.

        Si el GET ya trae datos de replay se guarda y marca como done; si no,
        la partida queda pending para reintentar en otra corrida.
        """
        done = 0
        not_ready = 0
        failed = 0

        index = 0
        while index < len(match_ids):
            match_id = match_ids[index]
            progress = f"[{index + 1}/{len(match_ids)}]"
            try:
                print(f"{progress} Consultando match {match_id}...")
                data = self.client.get_match(match_id)
                if data is not None and self._has_replay_data(data):
                    self.match_repository.save_match_details(match_id, data)
                    self.match_repository.update_parse_status(match_id, "done")
                    done += 1
                    print(f"  ✓ Match {match_id} guardado con datos de replay.")
                else:
                    self.match_repository.update_parse_status(match_id, "pending")
                    not_ready += 1
                    print(f"  → Match {match_id} aún sin datos de replay. Se reintentará en otra corrida.")
                index += 1
            except RateLimitError as exc:
                self._handle_rate_limit(exc)
                continue
            except Exception as exc:
                print(f"  ✗ Error consultando match {match_id}: {exc}")
                failed += 1
                index += 1

        return done, not_ready, failed

    def parse_unparsed(self) -> tuple[int, int, int, int, int]:
        match_ids = self.match_repository.list_unparsed(limit=Config.PARSE_BATCH_SIZE)
        if not match_ids:
            print("\nNo hay partidas pendientes de parseo.")
            return 0, 0, 0, 0, 0

        if Config.PARSE_GET_ONLY:
            print(f"\nProcesando lote de {len(match_ids)} partida(s) con OpenDota (solo GET)...")
            done, not_ready, failed = self._check_unparsed(match_ids)
            print(f"\nParseo finalizado:")
            print(f"  {done} partida(s) con datos de replay")
            print(f"  {not_ready} partida(s) aún sin datos (se reintentarán)")
            print(f"  {failed} partida(s) con error al consultar")
            return done, not_ready, failed, len(match_ids), 0

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

    def list_match_ids_csvs(self) -> list[Path]:
        """Return the available `match_ids_*.csv` exports, newest first."""
        return sorted(Config.EXPORT_DIR.glob("match_ids_*.csv"), reverse=True)

    def download_latest_match_ids_from_drive(self) -> Path | None:
        """Download the most recent `match_ids_*.csv` from Drive to exports/.

        Returns the local path of the downloaded file, or None on failure.
        """
        if self.drive_service is None or not self.drive_service.enabled:
            print("\nGoogle Drive no configurado en este equipo.")
            return None
        names = sorted(
            name for name in self.drive_service.list_files() if name.startswith("match_ids_")
        )
        if not names:
            print("\nNo hay archivos match_ids_*.csv en Google Drive.")
            return None
        remote_name = names[-1]
        dest = Config.EXPORT_DIR / remote_name
        if self.drive_service.download(remote_name, dest):
            return dest
        return None

    def count_pending_for_csv(self, csv_path: Path) -> int:
        """Return how many IDs in a `match_ids_*.csv` are still pending/queued/parsing."""
        match_ids = self._read_match_ids_csv(csv_path)
        return self.match_repository.count_pending_status(match_ids)

    def cleanup_consumed_csv(self, csv_path: Path) -> None:
        """Delete a processed `match_ids_*.csv` locally and on Drive.

        Only when every ID in the CSV is already `done` or `unparseable` in the
        local database, so pending matches are never lost.
        """
        match_ids = self._read_match_ids_csv(csv_path)
        if not match_ids:
            return
        pending = self.match_repository.count_pending_status(match_ids)
        if pending:
            print(
                f"\nQuedan {pending} partida(s) pendientes de parsear; "
                "el CSV no se elimina aún."
            )
            return
        if self.drive_service is not None:
            self.drive_service.delete(csv_path.name)
        csv_path.unlink(missing_ok=True)
        print(f"\n✓ Eliminado {csv_path.name} (local y de Google Drive).")

    def enqueue_from_csv(self, csv_path: Path) -> tuple[int, int, int]:
        """Enqueue replay parses for every ID in a `match_ids_*.csv`.

        Intended to run on a machine with its own OpenDota quota/IP (e.g. at the
        institute). Does not touch the local database. Writes a traceability CSV
        `parse_jobs_YYYY-MM-DD.csv` with the `(match_id, job_id)` pairs.
        """
        match_ids = self._read_match_ids_csv(csv_path)
        if not match_ids:
            print("\nEl CSV no contiene IDs válidos.")
            return 0, 0, 0

        print(f"\nEncolando parseo de {len(match_ids)} partida(s) desde {csv_path.name}...")
        enqueued = 0
        no_job = 0
        failed = 0
        jobs: list[tuple[int, str]] = []

        index = 0
        while index < len(match_ids):
            match_id = match_ids[index]
            progress = f"[{index + 1}/{len(match_ids)}]"
            try:
                job_id = self.client.request_parse(match_id)
                if job_id is None:
                    no_job += 1
                    print(f"  {progress} Match {match_id}: sin job (ya parseado o no disponible).")
                else:
                    enqueued += 1
                    jobs.append((match_id, job_id))
                    print(f"  ✓ {progress} Match {match_id}: encolado (job {job_id}).")
                index += 1
            except RateLimitError as exc:
                self._handle_rate_limit(exc)
                continue
            except Exception as exc:
                failed += 1
                print(f"  ✗ {progress} Error encolando match {match_id}: {exc}")
                index += 1

        self._write_jobs_csv(csv_path, jobs)
        print(f"\nEncolado finalizado:")
        print(f"  {enqueued} partida(s) encoladas")
        print(f"  {no_job} partida(s) sin job (ya parseadas o sin replay)")
        print(f"  {failed} partida(s) con error")
        return enqueued, no_job, failed

    def download_from_csv(self, csv_path: Path) -> tuple[int, int, int, int]:
        """Download parsed matches listed in a `match_ids_*.csv`.

        Intended to run at home after the parses were enqueued elsewhere. Skips
        matches already `done` with replay data and `unparseable` matches to save
        OpenDota quota. Matches whose parse is not ready yet stay `pending` so
        they can be retried on a later run.
        """
        match_ids = self._read_match_ids_csv(csv_path)
        if not match_ids:
            print("\nEl CSV no contiene IDs válidos.")
            return 0, 0, 0, 0

        downloadable = self.match_repository.list_downloadable(match_ids)
        skipped = len(match_ids) - len(downloadable)
        if skipped:
            print(f"\n  {skipped} partida(s) ya descargadas o no parseables, se omiten (ahorro de cuota).")

        if not downloadable:
            print("\nNo hay partidas pendientes de descargar en el CSV.")
            return 0, 0, skipped, 0

        print(f"\nDescargando {len(downloadable)} partida(s) desde {csv_path.name}...")
        downloaded = 0
        not_ready = 0
        failed = 0

        index = 0
        while index < len(downloadable):
            match_id = downloadable[index]
            progress = f"[{index + 1}/{len(downloadable)}]"
            try:
                print(f"{progress} Consultando match {match_id}...")
                data = self.client.get_match(match_id)
                if data is not None and self._has_replay_data(data):
                    self.match_repository.save_match_details(match_id, data)
                    downloaded += 1
                    print(f"  ✓ Match {match_id} guardado con datos de replay.")
                else:
                    self.match_repository.update_parse_status(match_id, "pending")
                    not_ready += 1
                    print(f"  → Match {match_id} aún sin datos de replay. Se reintentará en otra corrida.")
                index += 1
            except RateLimitError as exc:
                self._handle_rate_limit(exc)
                continue
            except Exception as exc:
                failed += 1
                print(f"  ✗ {progress} Error consultando match {match_id}: {exc}")
                index += 1

        print(f"\nDescarga finalizada:")
        print(f"  {downloaded} partida(s) descargadas con datos de replay")
        print(f"  {not_ready} partida(s) aún sin datos (se reintentarán)")
        print(f"  {skipped} partida(s) omitidas (ya listas o no parseables)")
        print(f"  {failed} partida(s) con error")
        return downloaded, not_ready, skipped, failed

    def _read_match_ids_csv(self, csv_path: Path) -> list[int]:
        if not csv_path.exists():
            print(f"\nNo existe el archivo {csv_path}.")
            return []
        match_ids: list[int] = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw = row.get("match_id")
                if raw is None or not str(raw).strip():
                    continue
                try:
                    match_ids.append(int(raw))
                except ValueError:
                    continue
        return match_ids

    def _write_jobs_csv(self, csv_path: Path, jobs: list[tuple[int, str]]) -> None:
        if not jobs:
            return
        out_name = f"parse_jobs_{csv_path.stem.replace('match_ids_', '')}.csv"
        out_path = Config.EXPORT_DIR / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["match_id", "job_id"])
            writer.writerows(jobs)
        print(f"\n✓ {len(jobs)} job(s) registrados en {out_path}")
