# Stratz Rampage Scraper

A small Python CLI that scrapes Dota 2 rampage matches from the Stratz GraphQL API, parses replay data through the OpenDota REST API, and exports chats and kills as CSV and Excel files.

---

## What it does

- Discovers Dota 2 matches containing rampages from Stratz.
- Stores match IDs and metadata in a local SQLite database.
- Parses match replays via OpenDota to extract kill logs and chat events.
- Exports the extracted data into daily CSV and Excel reports.

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
3. Run the application:
   ```bash
   python main.py
   ```

The app validates the API key at startup and will not launch without it.

---

## Project structure

```
.
├── main.py                  # Entry point
├── config.py                # Centralized configuration
├── database.py              # SQLite wrapper and migrations
├── data/
│   └── chat_wheel.json      # Local chat wheel catalog
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
│   └── models.py            # Domain dataclasses
├── services/                # Business logic
│   ├── discovery/           # Match discovery services
│   ├── chat_wheel_service.py
│   ├── export_service.py
│   ├── hero_service.py
│   └── parse_service.py
├── repositories/            # SQLite access layer
├── tests/                   # Test structure
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

---

## Notes

- UI strings and printed output are in Spanish.
- There are no tests, no linter configuration, and no CI setup.
- The `.env`, `data.db`, and `exports/` directories are ignored by Git.
