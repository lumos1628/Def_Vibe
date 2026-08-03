from api.client import StratzClient
from api.opendota_client import OpenDotaClient
from config import Config
from database import Database
from repositories.chat_wheel_repository import ChatWheelRepository
from repositories.hero_repository import HeroRepository
from repositories.match_repository import MatchRepository
from services.chat_wheel_service import ChatWheelService
from services.export_service import ExportService
from services.hero_service import HeroService
from services.parse_service import ParseService
from services.rampage_service import RampageService
from services.specific_top_service import SpecificTopService
from services.top_heroes_service import TopHeroesService


def show_main_menu() -> int | None:
    print("\n=== STRATZ RAMPAGE SCRAPER ===")
    print("1. Buscar y almacenar IDs")
    print("2. Parse")
    print("3. Exportar data")
    print("4. Salir")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3", "4"):
        return int(choice)
    return None


def show_search_menu() -> int | None:
    print("\n--- Buscar y almacenar IDs ---")
    print("1. Buscar top 60 héroes + jugadores + partidas")
    print("2. Buscar por rampage divine_inmortal")
    print("3. Buscar últimos 5 rampages por héroe")
    print("4. Buscar específica top")
    print("5. Volver al menú principal")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3", "4", "5"):
        return int(choice)
    return None


def run_search_menu(service_factory) -> None:
    while True:
        choice = show_search_menu()
        if choice is None:
            print("Opción inválida. Intenta de nuevo.")
            continue
        if choice == 1:
            top_heroes_service = service_factory.top_heroes_service()
            top_heroes_service.fetch_top_heroes_matches()
        elif choice == 2:
            rampage_service = service_factory.rampage_service()
            rampage_service.fetch_by_rampages()
        elif choice == 3:
            rampage_service = service_factory.rampage_service()
            rampage_service.fetch_latest_rampages()
        elif choice == 4:
            specific_top_service = service_factory.specific_top_service()
            specific_top_service.fetch_specific_top_matches()
        elif choice == 5:
            break


def show_export_menu() -> int | None:
    print("\n--- Exportar data ---")
    print("1. Exportar kills y chats")
    print("2. Re-exportar partidas parseadas hoy")
    print("3. Volver al menú principal")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3"):
        return int(choice)
    return None


def run_export_menu(service_factory) -> None:
    while True:
        choice = show_export_menu()
        if choice is None:
            print("Opción inválida. Intenta de nuevo.")
            continue
        if choice == 1:
            export_service = service_factory.export_service()
            export_service.export_chat_kills_csv()
        elif choice == 2:
            export_service = service_factory.export_service()
            export_service.reexport_parsed_today()
        elif choice == 3:
            break


def show_parse_menu() -> int | None:
    print("\n--- Parse ---")
    print("1. Parsear")
    print("2. Limpiar IDs antiguas")
    print("3. Salir")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3"):
        return int(choice)
    return None

def run_parse_menu(service_factory) -> None:
    while True:
        choice = show_parse_menu()
        if choice is None:
            print("Opción inválida. Intenta de nuevo.")
            continue
        if choice == 1:
            parse_service = service_factory.parse_service()
            parse_service.parse_unparsed()
        elif choice == 2:
            parse_service = service_factory.parse_service()
            parse_service.clean_old_matches()
        elif choice == 3:
            break


class ServiceFactory:
    def __init__(self) -> None:
        self.db = Database()
        self.client = StratzClient()
        self.opendota_client = OpenDotaClient()
        self.hero_repo = HeroRepository(self.db)
        self.match_repo = MatchRepository(self.db)
        self.chat_wheel_repo = ChatWheelRepository(self.db)

    def hero_service(self) -> HeroService:
        return HeroService(self.client, self.hero_repo)

    def chat_wheel_service(self) -> ChatWheelService:
        return ChatWheelService(self.chat_wheel_repo)

    def rampage_service(self) -> RampageService:
        return RampageService(self.client, self.hero_repo, self.match_repo)

    def top_heroes_service(self) -> TopHeroesService:
        return TopHeroesService(self.client, self.hero_repo, self.match_repo)

    def specific_top_service(self) -> SpecificTopService:
        return SpecificTopService(self.client, self.hero_repo, self.match_repo)

    def parse_service(self) -> ParseService:
        return ParseService(self.opendota_client, self.match_repo)

    def export_service(self) -> ExportService:
        return ExportService(self.hero_repo, self.match_repo, self.chat_wheel_repo)


def main() -> None:
    Config.validate()
    factory = ServiceFactory()
    factory.db.init()
    factory.db.migrate()
    factory.hero_service().ensure_synced()
    factory.chat_wheel_service().ensure_synced()

    while True:
        choice = show_main_menu()
        if choice is None:
            print("Opción inválida. Intenta de nuevo.")
            continue
        if choice == 1:
            run_search_menu(factory)
        elif choice == 2:
            run_parse_menu(factory)
        elif choice == 3:
            run_export_menu(factory)
        elif choice == 4:
            print("Saliendo...")
            break


if __name__ == "__main__":
    main()
