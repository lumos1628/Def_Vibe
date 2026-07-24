from api.client import StratzClient
from api.opendota_client import OpenDotaClient
from config import Config
from database import Database
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository
from services.hero_service import HeroService
from services.parse_service import ParseService
from services.rampage_service import RampageService


def show_main_menu() -> int | None:
    print("\n=== STRATZ RAMPAGE SCRAPER ===")
    print("1. Buscar y almacenar IDs")
    print("2. Parsear partidas con OpenDota")
    print("3. Salir")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3"):
        return int(choice)
    return None


def show_search_menu() -> int | None:
    print("\n--- Buscar y almacenar IDs ---")
    print("1. Buscar por top player (próximamente)")
    print("2. Buscar por rampages")
    print("3. Volver al menú principal")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3"):
        return int(choice)
    return None


def run_search_menu(service_factory) -> None:
    while True:
        choice = show_search_menu()
        if choice is None:
            print("Opción inválida. Intenta de nuevo.")
            continue
        if choice == 1:
            print("\nEsta opción aún no está implementada. Vuelve pronto.")
        elif choice == 2:
            rampage_service = service_factory.rampage_service()
            rampage_service.fetch_by_rampages()
        elif choice == 3:
            break


class ServiceFactory:
    def __init__(self) -> None:
        self.db = Database()
        self.client = StratzClient()
        self.opendota_client = OpenDotaClient()
        self.hero_repo = HeroRepository(self.db)
        self.match_repo = MatchRepository(self.db)

    def hero_service(self) -> HeroService:
        return HeroService(self.client, self.hero_repo)

    def rampage_service(self) -> RampageService:
        return RampageService(self.client, self.hero_repo, self.match_repo)

    def parse_service(self) -> ParseService:
        return ParseService(self.opendota_client, self.match_repo)


def main() -> None:
    Config.validate()
    factory = ServiceFactory()
    factory.db.init()
    factory.db.migrate()
    factory.hero_service().ensure_synced()

    while True:
        choice = show_main_menu()
        if choice is None:
            print("Opción inválida. Intenta de nuevo.")
            continue
        if choice == 1:
            run_search_menu(factory)
        elif choice == 2:
            parse_service = factory.parse_service()
            parse_service.parse_unparsed()
        elif choice == 3:
            print("Saliendo...")
            break


if __name__ == "__main__":
    main()
