# Stratz Rampage Scraper

A small Python CLI that scrapes Dota 2 matches containing **rampages** from the Stratz GraphQL API, parses replay data through the OpenDota REST API, and exports chat and kill events into daily CSV and Excel reports.

---

## What it does

- Runs a **daily harvest** that discovers up to 2900 new distinct match IDs (at most 7 days old) from Stratz: recent rampages for all heroes, pro player matches, leaderboards, and the most-played/highest-winrate heroes of the patch.
- Stores match IDs and metadata in a local SQLite database (`data.db`).
- Parses match replays via OpenDota and stores the full JSON per match under `data/replays/`.
- Exports the extracted data (chats, kills, and a styled Excel workbook) into daily reports.
- Builds a combined rampage ranking (speed + reactions) from the parsed replay files.
- Shares the `match_ids_*.csv` between machines through a **Google Drive folder** so a third party (e.g., a machine at the institute with its own OpenDota quota) can enqueue parses for the same IDs.

---

## Quick start

```bash
source venv/bin/activate
python main.py
```

The virtual environment `venv` is already committed to the repository and uses Python 3.12.

---

## Setup

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Set your `STRATZ_API_KEY` in `.env`.
3. (Optional) Configure Google Drive to share the `match_ids_*.csv` between machines:
   1. Create a project in Google Cloud Console, enable the **Google Drive API**, and create an **OAuth client ID** of type **Desktop app**; download its JSON to `data/drive_client_secret.json` (this file is gitignored). Publish the app ("In production") so the refresh token does not expire.
   2. In `.env`, set `GOOGLE_DRIVE_CLIENT_SECRETS=data/drive_client_secret.json` and `GOOGLE_DRIVE_FOLDER_ID=<id from the folder URL>`.
   3. The first time Drive is used, a browser opens to authorize with your Google account; the token is saved to `data/drive_token.json` (gitignored) and refreshed automatically afterwards.
4. Run the application:
   ```bash
   python main.py
   ```

The app validates the API key at startup and will not launch without it. Drive is optional: when unconfigured or unreachable, exports are only stored locally.

---

## Menus

```
1. Buscar y almacenar IDs   → daily harvest (menu 1 → option 1) + match_ids CSV upload
2. Parse                    → parse matches / enqueue from CSV / download from CSV / clean old IDs
3. Exportar data            → daily chats/kills CSV + Excel
4. Analizar data            → combined rampage ranking (speed + reactions)
5. Salir
```

The **only** file handled through Google Drive is `exports/match_ids_*.csv`:

- At home, the harvest uploads it right after generating it.
- At the institute, the parse menu downloads the most recent one from Drive when no local file exists, enqueues the parses, and keeps `parse_jobs_*.csv` local.
- Back at home, once every ID in the CSV is processed, the CLI offers to delete the CSV locally and on Drive.

Excel/chat/kill exports, the rampage ranking, the replay JSONs, and `parse_jobs_*.csv` stay **local only**.

---

## Project structure

```
.
├── main.py                  # Entry point
├── config.py                # Centralized configuration
├── database.py              # SQLite wrapper and migrations
├── data/
│   ├── chat_wheel.json      # Local chat wheel catalog
│   └── drive_client_secret.json  # Google Drive OAuth client secret (ignored by Git)
│   └── drive_token.json          # Google Drive OAuth token (ignored by Git)
├── data.db                  # Local SQLite database (ignored by Git)
├── exports/                 # Generated exports (ignored by Git)
├── api/                     # External API clients
│   ├── client.py            # Stratz GraphQL client
│   ├── opendota_client.py   # OpenDota REST client
│   └── queries.py           # GraphQL query strings
├── cli/                     # CLI menus and dependency injection
│   ├── factory.py           # ServiceFactory
│   └── menus.py             # Interactive menus
├── core/                    # Shared utilities and domain models
│   ├── time.py              # Timestamp parsing helpers
│   ├── models.py            # Domain dataclasses
│   └── replay_store.py      # Raw replay JSON files (data/replays/)
├── services/                # Business logic
│   ├── discovery/           # Match discovery services (base, daily harvest, legacy)
│   ├── analysis_service.py  # Rampage ranking (menu 4)
│   ├── chat_wheel_service.py
│   ├── drive_service.py     # Google Drive upload/download (match_ids CSV)
│   ├── export_service.py
│   ├── hero_service.py
│   └── parse_service.py
├── repositories/            # SQLite access layer
├── tests/                   # Test structure (prepared for future pytest)
├── docs/                    # Documentation
└── requirements.txt         # Python dependencies
```

---

## Documentation

- [Project Goal](docs/project_goal.md)
- [Architecture](docs/architecture.md)
- [Pipeline](docs/pipeline.md)
- [Data Model](docs/data_model.md)
- [Modules](docs/modules.md)
- [CSV/Excel Format](docs/csv_format.md)

---

## Dependencies

See `requirements.txt`:

- `requests` — HTTP client for OpenDota
- `python-dotenv` — Load environment variables from `.env`
- `cloudscraper` — Cloudflare bypass for Stratz
- `openpyxl` — Excel workbook generation
- `google-api-python-client` — Google Drive API (optional, for sharing the match IDs CSV)

---

## Notes

- UI strings and printed output are in Spanish.
- There are no tests yet (the `tests/` directory is prepared scaffolding for a future `pytest` suite), no linter configuration, and no CI setup.
- The `.env`, `data.db`, `data/drive_client_secret.json`, `data/drive_token.json`, `exports/`, and `__pycache__/` entries are ignored by Git.
