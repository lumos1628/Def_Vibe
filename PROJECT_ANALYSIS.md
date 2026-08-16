# Análisis del Proyecto: Stratz Rampage Scraper

## 1. Resumen del proyecto

**Stratz Rampage Scraper** es una CLI en Python 3.12 que recolecta partidas de Dota 2 con rampages desde la API GraphQL de Stratz, las parsea a través de la API REST de OpenDota y exporta los datos de chats y kills en archivos CSV y Excel.

- **Propósito:** Descubrir partidas donde un héroe realiza rampages, parsear sus repeticiones, exportar kills/chats y construir un ranking combinado de rampages.
- **Arquitectura:** Patrón por capas: `api` → `services` → `repositories` → `database`.
- **Persistencia:** SQLite local (`data.db`) + JSON crudo por partida en `data/replays/`.
- **Integraciones externas:** Stratz (GraphQL), OpenDota (REST) y Google Drive (solo el CSV de IDs).
- **Entrada:** Menú interactivo en consola (`main.py` → `cli/menus.py`).

---

## 2. Estructura de carpetas y archivos

```
/home/gabriel/Escritorio/Repos/Def/
├── .env                  # Variables de entorno (ignorado por .gitignore)
├── .env.example          # Plantilla con STRATZ_API_KEY y GOOGLE_*
├── .gitignore            # Ignora .env, data.db, exports/, __pycache__/, credenciales Drive
├── AGENTS.md             # Documentación para agentes
├── README.md             # Documentación de alto nivel
├── config.py             # Configuración centralizada
├── database.py           # Wrapper de SQLite + migraciones
├── main.py               # Único punto de entrada
├── requirements.txt      # Dependencias Python
├── data/
│   ├── chat_wheel.json             # Catálogo local de chat wheels
│   ├── drive_client_secret.json    # Client secret OAuth de Drive (ignorado)
│   ├── drive_token.json            # Token OAuth de Drive (ignorado)
│   └── replays/{match_date}/{match_id}.json
├── data.db               # Base de datos SQLite (ignorada)
├── exports/              # Exportaciones CSV/Excel y match_ids_*.csv (ignorada)
├── api/
│   ├── client.py         # Cliente GraphQL de Stratz
│   ├── opendota_client.py# Cliente REST de OpenDota
│   └── queries.py        # Cadenas GraphQL
├── cli/
│   ├── factory.py        # ServiceFactory (inyección de dependencias)
│   └── menus.py          # Menús interactivos
├── core/
│   ├── models.py         # Dataclasses de dominio
│   ├── replay_store.py   # Archivos JSON de replay por partida
│   └── time.py           # Helpers de tiempo
├── services/
│   ├── analysis_service.py
│   ├── chat_wheel_service.py
│   ├── discovery/        # daily_harvest_service.py, base.py + servicios legacy
│   ├── drive_service.py
│   ├── export_service.py
│   ├── hero_service.py
│   └── parse_service.py
└── repositories/
    ├── chat_wheel_repository.py
    ├── hero_repository.py
    └── match_repository.py
```

---

## 3. Punto de entrada y flujo de ejecución

### Punto de entrada

- **`main.py`** es el único entrypoint.
- Ejecución recomendada:
  ```bash
  source venv/bin/activate
  python main.py
  ```

### Flujo de inicialización (`main()`)

1. `Config.validate()` → verifica que exista `STRATZ_API_KEY`.
2. Crea `ServiceFactory`.
3. `factory.db.init()` → crea tablas si no existen.
4. `factory.db.migrate()` → añade columnas y tablas faltantes a DBs existentes.
5. `factory.hero_service().ensure_synced()` → sincroniza héroes si la tabla está vacía.
6. `factory.chat_wheel_service().ensure_synced()` → carga chat wheels si la tabla está vacía.
7. Bucle del menú principal.

### Menú principal

```
1. Buscar y almacenar IDs
2. Parse
3. Exportar data
4. Analizar data
5. Salir
```

#### Submenú: Buscar y almacenar IDs

```
1. Cosecha diaria     → DailyHarvestService.harvest() + export match_ids CSV (y subida a Drive)
2. Volver al menú principal
```

`RampageService`, `TopHeroesService` y `SpecificTopService` son servicios de discovery **legacy**: siguen existiendo y cableados en `ServiceFactory`, pero ningún menú los alcanza.

#### Submenú: Parse

```
1. Parsear                     → ParseService.parse_unparsed() (modo GET-only por defecto)
2. Encolar parses desde CSV    → ParseService.enqueue_from_csv() (Tecsup)
3. Descargar parses desde CSV  → ParseService.download_from_csv() (casa)
4. Limpiar IDs antiguas        → ParseService.clean_old_matches()
5. Volver al menú principal
```

#### Submenú: Exportar data

```
1. Exportar kills y chats                → ExportService.export_chat_kills()
2. Re-exportar partidas parseadas hoy    → ExportService.reexport_parsed_today()
3. Volver al menú principal
```

#### Submenú: Analizar data

```
1. Fecha específica   → AnalysisService.export_top(date_prefix)
2. Todas las fechas   → AnalysisService.export_top(None)
```

---

## 4. Configuración (`config.py`)

Clase `Config` centralizada con variables de entorno y constantes.

| Variable | Significado |
|----------|-------------|
| `STRATZ_API_KEY` | Token Bearer para Stratz GraphQL (obligatorio) |
| `OPENDOTA_API_KEY` | API key opcional para OpenDota |
| `GOOGLE_DRIVE_CLIENT_SECRETS` | Path al client secret OAuth de Drive (opcional) |
| `GOOGLE_DRIVE_TOKEN_PATH` | Dónde se guarda el token OAuth de Drive (opcional) |
| `GOOGLE_DRIVE_FOLDER_ID` | ID de la carpeta compartida de Drive (opcional) |
| `BASE_URL` | `https://api.stratz.com/graphql` |
| `OPENDOTA_BASE_URL` | `https://api.opendota.com/api` |
| `DB_PATH` | `data.db` |
| `REPLAY_DATA_DIR` | `data/replays` |
| `EXPORT_DIR` | `exports/` |
| `ANALYSIS_EXPORT_DIR` | `exports/rampages/` |
| `BRACKET` | `DIVINE_IMMORTAL` (servicios legacy) |
| `REQUEST_DELAY` | 0.5s entre llamadas Stratz |
| `OPENDOTA_REQUEST_DELAY` | 0.65s entre llamadas OpenDota |
| `RAMPAGE_TAKE` | 2 matches por héroe (legacy) |
| `MAX_REPLAY_AGE_DAYS` | 8 días máximo para parsear replay |
| `CLEAN_OLD_MATCHES_DAYS` | 7 días para limpieza |
| `PARSE_BATCH_SIZE` | 3000 partidas por lote |
| `PARSE_POLL_INTERVAL` | 150s entre rondas de polling |
| `PARSE_MAX_POLLS` | 4 rondas máximo |
| `PARSE_GET_ONLY` | True (modo solo-GET: no encola jobs) |
| `RATE_LIMIT_MAX_RETRIES` | 10 (429 consecutivos antes de pausar) |
| `RATE_LIMIT_PAUSE_SECONDS` | 300s |
| `ANALYSIS_TOP_N` | 10 (filas impresas en consola) |
| `ANALYSIS_REACTION_WINDOW_SECONDS` | 60s (ventana de reacciones) |
| `DAILY_MATCH_TARGET` | 2900 IDs nuevos por cosecha |
| `DAILY_MATCH_MAX_AGE_DAYS` | 7 días |
| `DAILY_RAMPAGE_TAKE` | 20 (máximo Stratz) |
| `PLAYERS_BATCH_SIZE` | 5 (máximo Stratz) |
| `TOP_HEROES_COUNT` | 60 (legacy) |
| `SPECIFIC_TOP_HEROES` | Diccionario `{hero_id: top_count}` (legacy + fase 3 de cosecha) |

---

## 5. Dependencias (`requirements.txt`)

| Paquete | Uso |
|---------|-----|
| `requests` | HTTP para OpenDota |
| `python-dotenv` | Cargar variables de `.env` |
| `cloudscraper` | Bypass de Cloudflare para Stratz |
| `openpyxl` | Generar archivos Excel `.xlsx` |
| `google-api-python-client` | API de Google Drive (opcional) |
| `google-auth` | Autenticación de Google (opcional) |
| `google-auth-httplib2` | Soporte HTTP para google-auth (opcional) |
| `google-auth-oauthlib` | Flujo OAuth de usuario para Drive (opcional) |

---

## 6. Capa API

### `api/client.py`

- **`StratzClient`**: cliente GraphQL para Stratz.
  - Usa `cloudscraper.create_scraper()`.
  - Envía `Authorization: Bearer {STRATZ_API_KEY}`.
  - Retries: hasta `Config.MAX_RETRIES` con backoff `attempt * 2`.
  - Lanza `StratzApiError` si la respuesta contiene `errors`.
  - `pause()`: espera `Config.REQUEST_DELAY`.

### `api/opendota_client.py`

- **`OpenDotaClient`**: cliente REST para OpenDota.
  - Delay de 0.65s entre requests (`Config.OPENDOTA_REQUEST_DELAY`).
  - Manejo de rate limit 429: espera `Retry-After` o backoff exponencial.
  - Si se reciben `RATE_LIMIT_MAX_RETRIES` 429 consecutivos, lanza `RateLimitError`.
  - Métodos principales:
    - `get_match(match_id)` → `GET /matches/{match_id}`
    - `request_parse(match_id)` → `POST /request/{match_id}`
    - `get_request_status(job_id)` → `GET /request/{job_id}`

### `api/queries.py`

Contiene las queries GraphQL, incluyendo las de la cosecha diaria: `RECENT_RAMPAGES_QUERY`, `PRO_PLAYERS_QUERY`, `PRO_RECENT_MATCHES_QUERY`, `PLAYERS_HERO_MATCHES_QUERY` y `HERO_STATS_WIN_WEEK_QUERY`.

---

## 7. Capa de servicios

### `services/hero_service.py` y `services/chat_wheel_service.py`

- Sincronizan catálogos (héroes y chat wheels) solo si la tabla está vacía (`ensure_synced()`).

### `services/discovery/` (búsqueda de partidas)

- **`DailyHarvestService`** — única vía de descubrimiento activa. Cosecha hasta `DAILY_MATCH_TARGET` IDs nuevos en fases priorizadas (rampages recientes de todos los héroes, partidas de pro players, leaderboards de héroes de mecánicas únicas, héroes más jugados y héroes con mayor winrate del parche). Deduplica globalmente por `match_id`.
- **Legacy (sin menú):** `RampageService`, `TopHeroesService`, `SpecificTopService` — siguen en `ServiceFactory` pero no son alcanzables.

### `services/parse_service.py`

- **`ParseService`**
  - Modo **GET-only** por defecto (`PARSE_GET_ONLY=True`): consulta `GET /matches/{id}`, guarda y marca `done` las que ya tienen datos de replay; deja `pending` las que no (se reintentarán). No encola jobs ni hace polling.
  - Modo legacy: encola parses (`POST /request/{id}`), hace polling de `jobId`s y reintenta la descarga directa.
  - Estados de parseo: `pending`, `queued`, `parsing`, `done`, `failed`/`unparseable`.
  - Maneja `RateLimitError` con pausa de `RATE_LIMIT_PAUSE_SECONDS` (300s).
  - `enqueue_from_csv()` (Tecsup): encola parses de un `match_ids_*.csv` y escribe `parse_jobs_YYYY-MM-DD.csv`.
  - `download_from_csv()` (casa): descarga los matches parseados de un CSV, filtrando por `list_downloadable()`.
  - `download_latest_match_ids_from_drive()`, `count_pending_for_csv()`, `cleanup_consumed_csv()`: integración con Drive.
  - `clean_old_matches(days)`: elimina partidas antiguas (filtrando por índice de `match_date`).

### `services/export_service.py`

- **`ExportService`**
  - Lee los JSON de `data/replays/` del día actual.
  - Detecta rampage: ventana de 5 kills consecutivas en ≤18 segundos en el `kills_log` del héroe.
  - Traduce chat wheels usando la tabla `chat_wheels`.
  - Genera tres archivos por día en `exports/YYYY-MM-DD/`:
    - `chats.csv`
    - `kills.csv`
    - `rampage_export_YYYY-MM-DD.xlsx` (con encabezado gris y filas alternadas verdes por match).
  - `export_match_ids_csv()` escribe `match_ids_YYYY-MM-DD.csv` y lo sube a Drive (cuando está configurado).

### `services/analysis_service.py`

- **`AnalysisService`** — construye el ranking combinado de rampages (menú 4) a partir de los archivos de replay, sin llamadas API. Puntaje rank-based por velocidad (`racha_seg`) y reacciones en chat (`n_reacciones`). Exporta `exports/rampages/rampages_YYYY-MM-DD.csv` o `rampages_all.csv`.

### `services/drive_service.py`

- **`DriveService`** — única integración con Google Drive. Autentica como el usuario vía flujo OAuth de app de escritorio (client secret + token local). Comparte únicamente el `match_ids_*.csv` entre la máquina de casa y la de Tecsup. Degrada con gracia si no está configurado.

---

## 8. Capa de repositorios

### `repositories/hero_repository.py`

- `upsert(heroes)`, `list_all()`, `count()`.

### `repositories/chat_wheel_repository.py`

- `upsert(entries)`, `get_by_id(chat_wheel_id)`, `count()`, `list_all()`.

### `repositories/match_repository.py`

- CRUD de `rampage_matches`, incluyendo `upsert()`, `exists_for_hero()`, `count_distinct()`, `list_all_match_ids()`.
- Flujo de parseo: `list_unparsed()`, `count_pending_status()`, `get_parse_state()`, `list_queued()`, transiciones de estado (`mark_data_verified`, `update_parse_status`, `mark_parse_requested`, `mark_parsed`).
- Almacenamiento de JSON: `save_match_details()` / `get_match_details()` delegan en `core/replay_store.ReplayStore`; la tabla `match_details` es solo un índice (`file_path`, `match_date`).
- Análisis: `list_dates_with_parsed()`, `list_parsed_rows_by_date()`.
- Exportación: `list_matches_to_export()`, `mark_exported()`, `clear_export_log_for_date()`, `clear_export_log_for_parsed_today()`.
- Limpieza: `delete_old_matches(days)`.

---

## 9. Base de datos (`database.py`)

Clase `Database` que envuelve SQLite.

### Tablas creadas por `init()`

| Tabla | Propósito |
|-------|-----------|
| `heroes` | Catálogo de héroes de Dota 2 |
| `rampage_matches` | Matches descubiertos con metadatos de parseo |
| `export_log` | Registro de matches ya exportados |
| `chat_wheels` | Catálogo de chat wheels |

### Tablas/columnas añadidas por `migrate()`

- Columnas en `rampage_matches`: `parsed`, `has_replay_data`, `data_verified`, `parse_requested_at`, `parse_request_count`, `parse_job_id`, `parse_status`, `last_parse_attempt_at`, `unparseable`.
- Tabla `match_details` — **solo índice** de los JSON guardados en `data/replays/{match_date}/{match_id}.json` (columnas `match_id`, `file_path`, `match_date`).
- Conversión de DBs legacy: el JSON que estaba en línea en la columna `opendota_data` se vuelca a archivos y la columna se elimina.

---

## 10. Formatos de exportación CSV

- `chats.csv` y `kills.csv` — ver `docs/csv_format.md` para el detalle de columnas.
- `match_ids_YYYY-MM-DD.csv` — una columna `match_id`, una fila por ID. Se sube a Drive.
- `parse_jobs_YYYY-MM-DD.csv` — `match_id` + `job_id` (Tecsup). Solo local.
- Excel `rampage_export_YYYY-MM-DD.xlsx` — hojas `Chats` y `Kills` con estilos (encabezado `#334155`, alternancia de verdes por match, auto-filtro, fila congelada).

---

## 11. Clases principales

| Clase | Archivo | Responsabilidad |
|-------|---------|-----------------|
| `Config` | `config.py` | Centralizar configuración |
| `Database` | `database.py` | Conexión, inicialización y migraciones |
| `ServiceFactory` | `cli/factory.py` | Inyección de dependencias |
| `StratzClient` | `api/client.py` | Llamadas GraphQL a Stratz |
| `OpenDotaClient` | `api/opendota_client.py` | Llamadas REST a OpenDota |
| `ReplayStore` | `core/replay_store.py` | Archivos JSON de replay |
| `DailyHarvestService` | `services/discovery/daily_harvest_service.py` | Cosecha diaria de IDs |
| `ParseService` | `services/parse_service.py` | Parseo de replays + flujo CSV/Drive |
| `ExportService` | `services/export_service.py` | Exportación CSV/Excel + match_ids |
| `AnalysisService` | `services/analysis_service.py` | Ranking combinado de rampages |
| `DriveService` | `services/drive_service.py` | Compartir match_ids_*.csv por Drive |
| `HeroRepository` | `repositories/hero_repository.py` | Acceso a tabla `heroes` |
| `MatchRepository` | `repositories/match_repository.py` | Acceso a `rampage_matches`, `match_details`, `export_log` |
| `ChatWheelRepository` | `repositories/chat_wheel_repository.py` | Acceso a tabla `chat_wheels` |

---

## 12. Observaciones importantes

1. **Sincronización lazy:** Héroes y chat wheels solo se sincronizan una vez (cuando las tablas están vacías).
2. **Crecimiento incremental:** `rampage_matches` usa `UNIQUE(hero_id, match_id)`; la cosecha además deduplica globalmente por `match_id`.
3. **Parseo con estado:** `pending` → `queued`/`parsing` → `done`/`failed`/`unparseable`, resumible entre ejecuciones.
4. **Manejo de rate limits:** OpenDota con delay de 0.65s, manejo de 429 y pausa larga tras 429 consecutivos; Stratz usa `cloudscraper` y retries.
5. **Límite de antigüedad:** Matches mayores a 8 días se marcan `unparseable`.
6. **JSON fuera de SQLite:** El JSON crudo de OpenDota vive en archivos por partida; la BD solo guarda el índice.
7. **Drive solo para IDs:** Únicamente `match_ids_*.csv` se comparte por Drive; el resto de artefactos es local.
8. **Detección de rampage:** 5 kills consecutivas dentro de una ventana de 18 segundos.
9. **Sin tests ni linter:** No hay suite de tests (solo scaffolding en `tests/`), ni linting, ni CI.
10. **venv en repo:** El entorno virtual está comiteado según `AGENTS.md`.
11. **Archivos ignorados:** `.env`, `data.db`, `exports/`, `__pycache__/`, `data/drive_client_secret.json`, `data/drive_token.json`, etc.
