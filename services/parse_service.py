from api.opendota_client import OpenDotaClient
from repositories.match_repository import MatchRepository


class ParseService:
    def __init__(
        self,
        client: OpenDotaClient,
        match_repository: MatchRepository,
    ) -> None:
        self.client = client
        self.match_repository = match_repository

    def parse_unparsed(self) -> tuple[int, int]:
        match_ids = self.match_repository.list_unparsed()
        if not match_ids:
            print("\nNo hay partidas pendientes de parseo.")
            return 0, 0

        print(f"\nParseando {len(match_ids)} partida(s) con OpenDota...")
        parsed_ok = 0
        parsed_failed = 0

        for index, match_id in enumerate(match_ids, start=1):
            print(f"[{index}/{len(match_ids)}] Match {match_id}: consultando OpenDota...")
            try:
                data = self.client.get_match(match_id)
                if data is None:
                    print(f"  → Match {match_id} no encontrado en OpenDota. Se marca como parseado para no reintentar.")
                    self.match_repository.mark_parsed(match_id)
                    parsed_failed += 1
                    continue

                self.match_repository.save_match_details(match_id, data)
                self.match_repository.mark_parsed(match_id)
                parsed_ok += 1
                print(f"  ✓ Match {match_id} parseado y guardado.")
            except Exception as exc:
                print(f"  ✗ Error parseando match {match_id}: {exc}. Se marca como parseado para no reintentar.")
                self.match_repository.mark_parsed(match_id)
                parsed_failed += 1

        print(f"\nParseo finalizado: {parsed_ok} exitoso(s), {parsed_failed} fallido(s) / no encontrado(s).")
        return parsed_ok, parsed_failed
