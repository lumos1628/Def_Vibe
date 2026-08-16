from cli.factory import ServiceFactory
from cli.menus import (
    show_main_menu,
    run_analysis_menu,
    run_export_menu,
    run_parse_menu,
    run_search_menu,
)
from config import Config


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
            run_analysis_menu(factory)
        elif choice == 5:
            print("Saliendo...")
            break


if __name__ == "__main__":
    main()
