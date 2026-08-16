from pathlib import Path

from cli.factory import ServiceFactory
from config import Config


def show_main_menu() -> int | None:
    print("\n=== STRATZ RAMPAGE SCRAPER ===")
    print("1. Buscar y almacenar IDs")
    print("2. Parse")
    print("3. Exportar data")
    print("4. Analizar data")
    print("5. Salir")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3", "4", "5"):
        return int(choice)
    return None


def show_search_menu() -> int | None:
    print("\n--- Buscar y almacenar IDs ---")
    print("1. Cosecha diaria (objetivo 2900 IDs nuevos)")
    print("2. Re-subir última CSV de IDs a Google Drive")
    print("3. Volver al menú principal")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3"):
        return int(choice)
    return None


def run_search_menu(service_factory: ServiceFactory) -> None:
    while True:
        choice = show_search_menu()
        if choice is None:
            print("Opción inválida. Intenta de nuevo.")
            continue
        if choice == 1:
            daily_harvest_service = service_factory.daily_harvest_service()
            saved_ids = daily_harvest_service.harvest()
            if saved_ids:
                export_service = service_factory.export_service()
                export_service.export_match_ids_csv(saved_ids)
        elif choice == 2:
            drive_service = service_factory.drive_service
            csvs = sorted(Config.EXPORT_DIR.glob("match_ids_*.csv"), reverse=True)
            if not csvs:
                print("\nNo hay archivos match_ids_*.csv en exports/ para subir.")
            else:
                latest = csvs[0]
                print(f"\nRe-subiendo {latest.name} a Google Drive...")
                drive_service.upload(latest)
        elif choice == 3:
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
    print("2. Encolar parses desde CSV (Tecsup)")
    print("3. Descargar parses desde CSV (casa)")
    print("4. Limpiar IDs antiguas")
    print("5. Volver al menú principal")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2", "3", "4", "5"):
        return int(choice)
    return None


def _pick_match_ids_csv(parse_service) -> Path | None:
    csvs = parse_service.list_match_ids_csvs()
    if not csvs:
        print("\nNo hay archivos match_ids_*.csv en exports/.")
        if getattr(parse_service, "drive_service", None) is not None:
            answer = input("¿Descargar el match_ids más reciente desde Google Drive? [s/N]: ").strip().lower()
            if answer in ("s", "si", "y", "yes"):
                downloaded = parse_service.download_latest_match_ids_from_drive()
                if downloaded is not None:
                    return downloaded
        print("Ejecuta primero la cosecha diaria (menú 1).")
        return None
    print("\nArchivos de IDs disponibles:")
    for idx, csv_path in enumerate(csvs, start=1):
        print(f"  {idx}. {csv_path.name}")
    selection = input("Selecciona un archivo: ").strip()
    try:
        num = int(selection)
    except ValueError:
        print("Opción inválida.")
        return None
    if 1 <= num <= len(csvs):
        return csvs[num - 1]
    print("Opción inválida.")
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
            csv_path = _pick_match_ids_csv(parse_service)
            if csv_path is not None:
                parse_service.enqueue_from_csv(csv_path)
        elif choice == 3:
            parse_service = service_factory.parse_service()
            csv_path = _pick_match_ids_csv(parse_service)
            if csv_path is not None:
                parse_service.download_from_csv(csv_path)
                pending = parse_service.count_pending_for_csv(csv_path)
                if pending == 0:
                    answer = input(
                        "\nTodos los IDs del CSV ya están procesados. "
                        "¿Eliminar el CSV (local y en Google Drive)? [s/N]: "
                    ).strip().lower()
                    if answer in ("s", "si", "y", "yes"):
                        parse_service.cleanup_consumed_csv(csv_path)
                else:
                    print(
                        f"\nQuedan {pending} partida(s) pendientes; el CSV se conserva "
                        "para reintentar en otra corrida."
                    )
        elif choice == 4:
            parse_service = service_factory.parse_service()
            parse_service.clean_old_matches()
        elif choice == 5:
            break


def show_analysis_menu() -> int | None:
    print("\n--- Analizar data ---")
    print("1. Exportar rampages (top combinado de rachas y reacciones)")
    print("2. Volver al menú principal")
    choice = input("Selecciona una opción: ").strip()
    if choice in ("1", "2"):
        return int(choice)
    return None


def run_analysis_menu(service_factory: ServiceFactory) -> None:
    while True:
        choice = show_analysis_menu()
        if choice is None:
            print("Opción inválida. Intenta de nuevo.")
            continue
        if choice == 1:
            analysis_service = service_factory.analysis_service()
            dates = analysis_service.list_dates()
            if not dates:
                print("\nNo hay partidas parseadas con datos de replay.")
                continue
            print("\nFechas con partidas parseadas:")
            for idx, (date_str, count) in enumerate(dates, start=1):
                print(f"  {idx}. {date_str} ({count} IDs)")
            print(f"  {len(dates) + 1}. Todas las fechas")
            selection = input("Selecciona una opción: ").strip()
            try:
                num = int(selection)
            except ValueError:
                print("Opción inválida.")
                continue
            if num == len(dates) + 1:
                analysis_service.export_top(None)
            elif 1 <= num <= len(dates):
                analysis_service.export_top(dates[num - 1][0])
            else:
                print("Opción inválida.")
        elif choice == 2:
            break
