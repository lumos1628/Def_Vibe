# Análisis del Proyecto: Stratz Rampage Scraper

## 1. Resumen del proyecto

**Stratz Rampage Scraper** es una CLI en Python 3.12 que recolecta partidas de Dota 2 con rampages desde la API GraphQL de Stratz, las parsea a través de la API REST de OpenDota y exporta los datos de chats y kills en archivos CSV y Excel.

- **Propósito:** Buscar partidas donde un héroe realiza rampages, parsear sus repeticiones y exportar kills/chats.
- **Arquitectura:** Patrón por capas: `api` → `services` → `repositories` → `database`.
- **Persistencia:** SQLite local (`data.db`).
- **Entrada:** Menú interactivo en consola (`main.py`).

---

## 2. Estructura de carpetas y archivos

```
/home/gabriel/Escritorio/Repos/Def/
├── .env                  # Variables de entorno (ignorado por .gitignore)
├── .env.example          # Plantilla con STRATZ_API_KEY
├── .gitignore            # Ignora .env, data.db, exports/, __pycache__/
├── AGENTS.md             # Documentación para agentes
├── config.py             # Configuración centralizada
├── data/
│   └── chat_wheel.json   # Catálogo local de chat wheels
├── data.db               # Base de datos SQLite (ignorada)
├── database.py           # Wrapper de SQLite + migraciones
├── main.py               # Punto de entrada y menús
├── requirements.txt      # Dependencias Python
├── api/
│   ├── __init__.py
│   ├── client.py         # Cliente GraphQL de Stratz
│   ├── opendota_client.py# Cliente REST de OpenDota
│   └── queries.py        # Cadenas GraphQL
├── services/
│   ├── __init__.py
│   ├── chat_wheel_service.py
│   ├── export_service.py
│   ├── hero_service.py
│   ├── parse_service.py
│   ├── rampage_service.py
│   ├── specific_top_service.py
│   └── top_heroes_service.py
└── repositories/
    ├── __init__.py
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
4. Salir
```

#### Submenú: Buscar y almacenar IDs

```
1. Buscar top 60 héroes + jugadores + partidas     → TopHeroesService.fetch_top_heroes_matches()
2. Buscar por rampage divine_inmortal              → RampageService.fetch_by_rampages()
3. Buscar últimos 5 rampages por héroe             → RampageService.fetch_latest_rampages()
4. Buscar específica top                           → SpecificTopService.fetch_specific_top_matches()
5. Volver al menú principal
```

#### Submenú: Parse

```
1. Parsear           → ParseService.parse_unparsed()
2. Limpiar IDs antiguas → ParseService.clean_old_matches()
3. Salir
```

#### Submenú: Exportar data

```
1. Exportar kills y chats                → ExportService.export_chat_kills_csv()
2. Re-exportar partidas parseadas hoy    → ExportService.reexport_parsed_today()
3. Volver al menú principal
```

---

## 4. Configuración (`config.py`)

Clase `Config` centralizada con variables de entorno y constantes.

| Variable | Significado |
|----------|-------------|
| `STRATZ_API_KEY` | Token Bearer para Stratz GraphQL |
| `OPENDOTA_API_KEY` | API key opcional para OpenDota |
| `BASE_URL` | `https://api.stratz.com/graphql` |
| `OPENDOTA_BASE_URL` | `https://api.opendota.com/api` |
| `DB_PATH` | `data.db` |
| `EXPORT_DIR` | `exports/` |
| `BRACKET` | `DIVINE_IMMORTAL` |
| `REQUEST_DELAY` | 0.5s entre llamadas Stratz |
| `OPENDOTA_REQUEST_DELAY` | 1.0s entre llamadas OpenDota |
| `RAMPAGE_TAKE` | 2 matches por héroe en búsqueda de rampages |
| `MAX_REPLAY_AGE_DAYS` | 8 días máximo para parsear replay |
| `CLEAN_OLD_MATCHES_DAYS` | 7 días para limpieza manual |
| `PARSE_BATCH_SIZE` | 1000 partidas por lote |
| `PARSE_POLL_INTERVAL` | 300s entre rondas de polling |
| `PARSE_MAX_POLLS` | 4 rondas máximo |
| `TOP_HEROES_COUNT` | 60 héroes top |
| `TOP_PLAYERS_PER_HERO` | 3 jugadores top por héroe |
| `TOP_MATCHES_PER_PLAYER` | 3 partidas por jugador |
| `SPECIFIC_TOP_HEROES` | Diccionario `{hero_id: top_count}` para búsqueda específica |
| `HERO_STATS_BRACKETS` | Todos los brackets de ranked |

---

## 5. Dependencias (`requirements.txt`)

| Paquete | Uso |
|---------|-----|
| `requests>=2.31.0` | HTTP para OpenDota |
| `python-dotenv>=1.0.0` | Cargar variables de `.env` |
| `cloudscraper>=1.2.71` | Bypass de Cloudflare para Stratz |
| `openpyxl>=3.1.2` | Generar archivos Excel `.xlsx` |

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
  - Manejo de rate limit 429: espera `Retry-After` o backoff exponencial.
  - Si se reciben `RATE_LIMIT_MAX_RETRIES` 429 consecutivos, lanza `RateLimitError`.
  - `pause()`: espera `Config.OPENDOTA_REQUEST_DELAY` después de cada request.
  - Métodos principales:
    - `get_match(match_id)` → `GET /matches/{match_id}`
    - `request_parse(match_id)` → `POST /request/{match_id}`
    - `get_request_status(job_id)` → `GET /request/{job_id}`

### `api/queries.py`

Contiene las queries GraphQL:

| Query | Uso |
|-------|-----|
| `HEROES_QUERY` | Listar héroes (id, displayName, shortName) |
| `RAMPAGES_QUERY` | Rampages por héroe + bracket |
| `LATEST_RAMPAGES_QUERY` | Últimos rampages por héroe (sin bracket) |
| `MATCH_DATE_QUERY` | Fecha de inicio de una partida |
| `HERO_STATS_WIN_WEEK_QUERY` | Héroes más jugados por bracket |
| `LEADERBOARD_HERO_QUERY` | Top jugadores de un héroe |
| `PLAYER_MATCHES_QUERY` | Partidas recientes de un jugador |

---

## 7. Capa de servicios

### `services/hero_service.py`

- **`HeroService`**
  - `sync()`: descarga héroes desde Stratz y los guarda.
  - `ensure_synced()`: solo sincroniza si la tabla está vacía.

### `services/chat_wheel_service.py`

- **`ChatWheelService`**
  - `sync()`: carga `data/chat_wheel.json` y guarda en BD.
  - `ensure_synced()`: solo sincroniza si la tabla está vacía.

### `services/rampage_service.py`

- **`RampageService`**
  - Itera sobre todos los héroes sincronizados.
  - Busca rampages en Stratz para cada héroe.
  - Para cada match nuevo, hace una segunda llamada para obtener `startDateTime`.
  - Guarda en `rampage_matches` con `UNIQUE(hero_id, match_id)`.
  - Métodos:
    - `fetch_by_rampages()` → bracket `DIVINE_IMMORTAL`, `take = RAMPAGE_TAKE`.
    - `fetch_latest_rampages()` → sin bracket, `take = 5`.

### `services/top_heroes_service.py`

- **`TopHeroesService`**
  - Obtiene los 60 héroes más jugados (`winWeek`).
  - Para cada uno, obtiene top 3 jugadores (`leaderboard`).
  - Para cada jugador, obtiene sus últimas 3 partidas con ese héroe.
  - Guarda matches en `rampage_matches`.

### `services/specific_top_service.py`

- **`SpecificTopService`**
  - Similar a `TopHeroesService` pero para un conjunto fijo de héroes definidos en `Config.SPECIFIC_TOP_HEROES`.
  - Permite buscar top 50/25/10/5 jugadores por héroe específico.

### `services/parse_service.py`

- **`ParseService`**
  - Procesa lotes de partidas no parseadas.
  - Fases:
    1. **_enqueue_unparsed**: verifica match con `GET /matches/{match_id}`, guarda JSON en `match_details`. Si no tiene replay data y no es muy antiguo, encola parseo.
    2. **_poll_jobs**: consulta estado de jobs encolados periódicamente.
    3. **_fetch_done_matches**: reintenta obtener datos de matches que aún estén encolados.
  - Estados de parseo: `pending`, `queued`, `parsing`, `done`, `failed`.
  - Maneja `RateLimitError` con pausa de 300s.
  - `clean_old_matches(days)`: elimina partidas antiguas.

### `services/export_service.py`

- **`ExportService`**
  - Lee `match_details` del día actual.
  - Detecta rampage: ventana de 5 kills consecutivas en ≤18 segundos en el `kills_log` del héroe.
  - Traduce chat wheels usando la tabla `chat_wheels`.
  - Genera tres archivos por día en `exports/YYYY-MM-DD/`:
    - `chats.csv`
    - `kills.csv`
    - `rampage_export_YYYY-MM-DD.xlsx` (con estilos dark-mode y filas coloreadas por match).

---

## 8. Capa de repositorios

### `repositories/hero_repository.py`

- **`HeroRepository`**
  - `upsert(heroes)`: inserta/actualiza héroes.
  - `list_all()`: devuelve todos los héroes.
  - `count()`: delega a `Database.count_heroes()`.

### `repositories/chat_wheel_repository.py`

- **`ChatWheelRepository`**
  - `upsert(entries)`: inserta/actualiza chat wheels.
  - `get_by_id(chat_wheel_id)`: busca un chat wheel por ID.
  - `count()`, `list_all()`.

### `repositories/match_repository.py`

- **`MatchRepository`**
  - `upsert(match_id, hero_id, played_at, steam_account_id)`: guarda match.
  - `exists_for_hero(...)`: evita duplicados por héroe/match.
  - `list_unparsed(limit)`: matches pendientes de parseo.
  - `list_queued()`: matches con `job_id` en estado `queued`/`parsing`.
  - `mark_parse_requested(...)`: actualiza estado a `queued`.
  - `mark_parsed(...)`: marca como `done`/`failed`.
  - `save_match_details(...)`: guarda JSON de OpenDota y actualiza flags.
  - `list_matches_to_export(today_iso)`: matches parseados hoy no exportados.
  - `mark_exported(...)`: registra exportación en `export_log`.
  - `delete_old_matches(days)`: limpia partidas antiguas.

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

- Columnas en `rampage_matches`:
  - `parsed`, `has_replay_data`, `data_verified`
  - `parse_requested_at`, `parse_request_count`, `parse_job_id`
  - `parse_status`, `last_parse_attempt_at`, `unparseable`
- Tabla `match_details` (JSON de OpenDota por match).
- Índices adicionales.
- Backfills para compatibilidad con DBs antiguas.

### Esquema detallado

**heroes**
- `id INTEGER PRIMARY KEY`
- `display_name TEXT NOT NULL`
- `short_name TEXT NOT NULL`
- `synced_at TEXT NOT NULL`

**rampage_matches**
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `match_id INTEGER NOT NULL`
- `hero_id INTEGER NOT NULL`
- `played_at TEXT NOT NULL`
- `steam_account_id INTEGER NOT NULL`
- `extracted_at TEXT NOT NULL`
- `parsed INTEGER DEFAULT 0`
- `has_replay_data INTEGER DEFAULT 0`
- `data_verified INTEGER DEFAULT 0`
- `parse_requested_at TEXT`
- `parse_request_count INTEGER DEFAULT 0`
- `parse_job_id TEXT`
- `parse_status TEXT DEFAULT 'pending'`
- `last_parse_attempt_at TEXT`
- `unparseable INTEGER DEFAULT 0`
- `UNIQUE(hero_id, match_id)`

**match_details**
- `match_id INTEGER PRIMARY KEY`
- `opendota_data TEXT NOT NULL`
- `parsed_at TEXT NOT NULL`

**export_log**
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `match_id INTEGER NOT NULL`
- `exported_at TEXT NOT NULL`
- `output_path TEXT NOT NULL`
- `UNIQUE(match_id)`

**chat_wheels**
- `id INTEGER PRIMARY KEY`
- `name TEXT NOT NULL`
- `label TEXT NOT NULL`
- `message TEXT NOT NULL`
- `all_chat INTEGER DEFAULT 0`
- `synced_at TEXT NOT NULL`

---

## 10. Formatos de exportación CSV

### `chats.csv`

Campos (`CHAT_FIELDNAMES`):

| Campo | Descripción |
|-------|-------------|
| `match_id` | ID de la partida |
| `chat_time` | Tiempo del mensaje en segundos |
| `chat_time_min` | Tiempo en minutos |
| `chat_message` | Texto del mensaje o chat wheel resuelto |
| `chat_type` | Tipo de mensaje (ej. `chatwheel`) |
| `chat_is_chatwheel` | 1 si es chat wheel, 0 si no |
| `chat_wheel_id` | ID del chat wheel (si aplica) |
| `sender_hero_id` | ID del héroe que envió el mensaje |
| `sender_hero_name` | Nombre del héroe |
| `sender_slot` | Slot del emisor |
| `sender_player_slot` | `player_slot` del emisor |
| `has_replay_data` | 1 si hay datos de replay |
| `unparseable` | 1 si es no parseable |

### `kills.csv`

Campos (`KILL_FIELDNAMES`):

| Campo | Descripción |
|-------|-------------|
| `match_id` | ID de la partida |
| `kill_time` | Tiempo de la kill en segundos |
| `kill_time_min` | Tiempo en minutos |
| `killer_hero_id` | ID del héroe asesino |
| `killer_hero_name` | Nombre del asesino |
| `victim_hero_id` | ID del héroe víctima |
| `victim_hero_name` | Nombre de la víctima |
| `rampage_time` | Tiempo de inicio del rampage detectado |
| `rampage_time_min` | Rampage time en minutos |
| `is_rampage_kill` | 1 si la kill pertenece al rampage |
| `has_replay_data` | 1 si hay datos de replay |
| `unparseable` | 1 si es no parseable |

### Excel

- Hojas: `Chats`, `Kills`.
- Estilo dark-mode con encabezado gris (`#334155`) y texto blanco.
- Filas coloreadas alternando verde claro/oscuro por partida.
- Auto-filtro y paneles congelados.

---

## 11. Clases y funciones principales

### Clases principales

| Clase | Archivo | Responsabilidad |
|-------|---------|-----------------|
| `Config` | `config.py` | Centralizar configuración |
| `Database` | `database.py` | Conexión, inicialización y migraciones |
| `ServiceFactory` | `main.py` | Inyección de dependencias |
| `StratzClient` | `api/client.py` | Llamadas GraphQL a Stratz |
| `OpenDotaClient` | `api/opendota_client.py` | Llamadas REST a OpenDota |
| `StratzApiError` | `api/client.py` | Error de API Stratz |
| `RateLimitError` | `api/opendota_client.py` | Rate limit de OpenDota |
| `HeroService` | `services/hero_service.py` | Sincronización de héroes |
| `ChatWheelService` | `services/chat_wheel_service.py` | Sincronización de chat wheels |
| `RampageService` | `services/rampage_service.py` | Búsqueda de rampages |
| `TopHeroesService` | `services/top_heroes_service.py` | Búsqueda por top héroes/jugadores |
| `SpecificTopService` | `services/specific_top_service.py` | Búsqueda específica por héroe |
| `ParseService` | `services/parse_service.py` | Parseo de replays |
| `ExportService` | `services/export_service.py` | Exportación CSV/Excel |
| `HeroRepository` | `repositories/hero_repository.py` | Acceso a tabla `heroes` |
| `MatchRepository` | `repositories/match_repository.py` | Acceso a `rampage_matches`, `match_details`, `export_log` |
| `ChatWheelRepository` | `repositories/chat_wheel_repository.py` | Acceso a tabla `chat_wheels` |

### Funciones principales

- `main()` → punto de entrada.
- `show_main_menu()`, `show_search_menu()`, `show_parse_menu()`, `show_export_menu()` → menús.
- `run_search_menu()`, `run_parse_menu()`, `run_export_menu()` → dispatchers de menús.
- `ServiceFactory` crea instancias de servicios.

---

## 12. Responsabilidades por módulo

| Módulo | Responsabilidad |
|--------|-----------------|
| `main.py` | Orquestación, menús, inyección de dependencias |
| `config.py` | Configuración y validación de entorno |
| `database.py` | Esquema SQLite y migraciones |
| `api/client.py` | Cliente Stratz GraphQL |
| `api/opendota_client.py` | Cliente OpenDota REST |
| `api/queries.py` | Definición de queries GraphQL |
| `services/hero_service.py` | Sincronizar catálogo de héroes |
| `services/chat_wheel_service.py` | Sincronizar catálogo de chat wheels |
| `services/rampage_service.py` | Buscar partidas por rampages |
| `services/top_heroes_service.py` | Buscar partidas de top héroes/jugadores |
| `services/specific_top_service.py` | Buscar partidas de héroes específicos |
| `services/parse_service.py` | Parsear replays con OpenDota |
| `services/export_service.py` | Exportar datos a CSV/Excel |
| `repositories/hero_repository.py` | Persistencia de héroes |
| `repositories/match_repository.py` | Persistencia de matches, detalles y logs |
| `repositories/chat_wheel_repository.py` | Persistencia de chat wheels |

---

## 13. Observaciones importantes

1. **Sincronización lazy:** Héroes y chat wheels solo se sincronizan una vez (cuando las tablas están vacías).
2. **Crecimiento incremental:** `rampage_matches` usa `UNIQUE(hero_id, match_id)`, por lo que re-ejecutar no duplica matches.
3. **Parseo con estado:** El flujo de parseo maneja estados (`pending` → `queued`/`parsing` → `done`/`failed`) y es resumible.
4. **Manejo de rate limits:** OpenDota tiene pausa de 1s y manejo de 429; Stratz usa `cloudscraper` y retries.
5. **Límite de antigüedad:** Matches mayores a 8 días se marcan `unparseable`.
6. **Exportación por día:** Los exports se organizan en carpetas `exports/YYYY-MM-DD/`.
7. **Colores en Excel:** Alternancia de verdes por `match_id` para facilitar lectura.
8. **Detección de rampage:** 5 kills consecutivas dentro de una ventana de 18 segundos.
9. **Sin tests ni linter:** El proyecto no tiene suite de tests, ni configuración de linting, ni CI.
10. **venv en repo:** El entorno virtual está comiteado según `AGENTS.md`.
11. **Archivos ignorados:** `.env`, `data.db`, `exports/`, `__pycache__/`, `*.pyc`, `*.pyo`, `*.pyd`.
