# Project Goal

## Purpose

The **Stratz Rampage Scraper** is a command-line tool built to collect and analyze Dota 2 matches that contain **rampages** — a sequence of five consecutive kills by a single player without dying.

## Objectives

1. **Discover rampage matches**
   - Query the Stratz GraphQL API for matches where heroes achieved rampages.
   - Search by ranked bracket (default: `DIVINE_IMMORTAL`).
   - Optionally search the latest rampages per hero or top players for specific heroes.

2. **Collect match metadata**
   - Store match IDs, hero IDs, player Steam account IDs, and match timestamps.
   - Avoid duplicates by enforcing a unique constraint on `(hero_id, match_id)`.

3. **Parse replay data**
   - Use the OpenDota REST API to request and poll replay parsing.
   - Extract kill logs and chat events from parsed replays.
   - Skip matches whose replays are no longer available (older than 8 days by default).

4. **Export structured reports**
   - Generate daily CSV files for chats and kills.
   - Generate a styled Excel workbook with two sheets: `Chats` and `Kills`.
   - Resolve chat wheel IDs into human-readable text.
   - Flag kills that belong to the detected rampage window.

## Data sources

- **Stratz GraphQL API** — match discovery, hero catalog, leaderboards, player matches.
- **OpenDota REST API** — replay parsing and detailed match data.
- **Local JSON catalog** (`data/chat_wheel.json`) — chat wheel translations.

## Target users

This tool is designed for anyone who wants to analyze Dota 2 rampage patterns, correlate them with in-game chat behavior, and produce reproducible datasets from real match data.
