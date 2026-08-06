from cli.factory import ServiceFactory


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


def run_search_menu(service_factory: ServiceFactory) -> None:
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


def run_export_menu(service_factory: ServiceFactory) -> None:
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
    print("3. Volver al menú principal")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3"):
        return int(choice)
    return None


def run_parse_menu(service_factory: ServiceFactory) -> None:
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
