# Project Goal

## Purpose

The **Stratz Rampage Scraper** is a command-line tool built to collect and analyze Dota 2 matches that contain **rampages** — a sequence of five consecutive kills by a single player without dying.

## Objectives

1. **Discover matches daily**
   - Run a **daily harvest** that collects up to `Config.DAILY_MATCH_TARGET` (2900) new distinct match IDs, at most `Config.DAILY_MATCH_MAX_AGE_DAYS` (7) days old, deduplicated globally.
   - The harvest runs five phases in priority order and stops once the target is reached: recent rampages for all heroes, recent matches of pro players, top leaderboard players of `Config.SPECIFIC_TOP_HEROES`, most-played heroes of the patch, and highest-winrate heroes.
   - After each harvest, the CLI exports the collected IDs to `exports/match_ids_YYYY-MM-DD.csv` and uploads it to Google Drive so another machine can parse them with its own OpenDota quota.

2. **Collect match metadata**
   - Store match IDs, hero IDs, player Steam account IDs, and match timestamps.
   - Avoid duplicates by enforcing a unique constraint on `(hero_id, match_id)`.

3. **Parse replay data**
   - Use the OpenDota REST API to request, poll, and download replay parsing.
   - The parsing can run on a separate machine: the institute enqueues parses from the shared `match_ids_*.csv` (`parse_jobs_*.csv`), and the home machine downloads the parsed matches.
   - Save the full OpenDota JSON per match at `data/replays/{match_date}/{match_id}.json`.
   - Skip or mark as `unparseable` matches whose replays are no longer available.

4. **Export structured reports**
   - Generate daily CSV files for chats and kills plus a styled Excel workbook with two sheets: `Chats` and `Kills`.
   - Resolve chat wheel IDs into human-readable text.
   - Flag kills that belong to the detected rampage window (5 kills within 18 seconds).

5. **Analyze rampages**
   - Build a combined rampage ranking from the parsed replay files (no API calls): rank-based score that rewards the shortest 5-kill window and the most in-game chat reactions.
   - Output a CSV per selected date or across all dates at `exports/rampages/`.

## Data sources

- **Stratz GraphQL API** — match discovery, hero catalog, leaderboards, player matches.
- **OpenDota REST API** — replay parsing and detailed match data.
- **Google Drive API** — sharing the `match_ids_*.csv` between the home machine and the parsing machine (optional).
- **Local JSON catalog** (`data/chat_wheel.json`) — chat wheel translations.

## Target users

This tool is designed for anyone who wants to analyze Dota 2 rampage patterns, correlate them with in-game chat behavior, and produce reproducible datasets from real match data.
