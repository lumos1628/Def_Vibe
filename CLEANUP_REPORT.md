# Cleanup Report

## Summary

Several elements were identified that could be cleaned up or refactored. None of them affect the current functionality of the program, but addressing them would reduce technical debt and improve maintainability.

---

## 1. Dead code / unused functions

### `Config.EXPORT_WINDOW_SECONDS`
- **Location:** `config.py`, line 17.
- **Status:** Defined as `None`, never read by any file.
- **Recommended action:** Remove the constant or implement the feature it was meant to control.

### `MatchRepository.count_by_hero()`
- **Location:** `repositories/match_repository.py`, lines 35-41.
- **Status:** Defined, never called.
- **Recommended action:** Remove if not planned for use; otherwise expose it through a menu or report.

### `MatchRepository.list_all()`
- **Location:** `repositories/match_repository.py`, lines 43-55.
- **Status:** Defined, never called by any service or menu.
- **Recommended action:** Remove or use in a future listing/monitor feature.

### `MatchRepository.list_all_match_details()`
- **Location:** `repositories/match_repository.py`, lines 253-259.
- **Status:** Defined, never called.
- **Recommended action:** Remove.

### `ChatWheelRepository.list_all()`
- **Location:** `repositories/chat_wheel_repository.py`, lines 57-63.
- **Status:** Defined, never called.
- **Recommended action:** Remove.

---

## 2. Duplicate functions

### `_parse_timestamp()`
- **Locations:**
  - `services/rampage_service.py`, lines 111-116.
  - `services/top_heroes_service.py`, lines 145-150.
  - `services/specific_top_service.py`, lines 115-120.
- **Issue:** Three identical implementations.
- **Recommended action:** Extract to a shared helper, e.g., `utils/time_utils.py` or a function in `database.py`/`config.py`, and reuse across the three services.

### Top player + match fetching
- **Locations:**
  - `services/top_heroes_service.py`, methods `_fetch_top_players` and `_fetch_player_matches`.
  - `services/specific_top_service.py`, methods `_fetch_top_players` and `_fetch_player_matches`.
- **Issue:** Nearly identical logic. The only difference is the `take` value for top players.
- **Recommended action:** Extract to a shared helper or base class, or refactor `SpecificTopService` to reuse `TopHeroesService` with a custom hero map.

### Match saving loops
- **Locations:**
  - `services/top_heroes_service.py`, lines 53-80.
  - `services/specific_top_service.py`, lines 47-74.
- **Issue:** Very similar structure: iterate players → iterate matches → check duplicate → upsert.
- **Recommended action:** Unify into an auxiliary function.

---

## 3. Unnecessary imports

No completely unused imports were found. All standard library and third-party imports are used at runtime or in type hints.

**Minor note:**
- In `parse_service.py`, the method `_has_replay_data` is an instance wrapper around the static method `MatchRepository.has_replay_data()`. It is not an unnecessary import, but it is a redundant indirection that could be simplified.

---

## 4. Unused variables

### Return value of `parse_unparsed()`
- **Location:** `services/parse_service.py`, line 192.
- **Status:** Returns a tuple `(total_done, queued, still_queued, failed, len(match_ids))`.
- **Issue:** In `main.py`, `run_parse_menu()` calls the method but does not capture or use the returned value.
- **Recommended action:** Keeping the return value is useful for tests or logging, but the statistics could at least be logged from within `parse_unparsed()` to make use of the information.

---

## 5. Unused / abandoned files

No abandoned Python files were found in the repository. All `.py` files are part of the active package structure:

- `main.py`
- `config.py`
- `database.py`
- `api/*.py`
- `services/*.py`
- `repositories/*.py`

The `__init__.py` files are empty but are required for the directories to be Python packages.

---

## 6. Minor inconsistencies

### Parse menu wording
- **Location:** `main.py`, line 95.
- **Issue:** The parse submenu exit option says `"3. Salir"` while the other submenus use `"Volver al menú principal"`.
- **Recommended action:** Change to `"3. Volver al menú principal"` for consistency.

### Shared `MAX_RETRIES` constant
- **Location:** `config.py`, line 18.
- **Issue:** `MAX_RETRIES` is used for Stratz (`api/client.py`) as an implicit default. The name is generic and could become confusing if more clients are added.
- **Recommended action:** Consider renaming to `STRATZ_MAX_RETRIES` for clarity (with care not to break `api/client.py`).

### `pause()` behavior in clients
- **Location:** `api/client.py` and `api/opendota_client.py`.
- **Observation:** `StratzClient.pause()` must be called manually after each `execute()`. `OpenDotaClient.pause()` runs automatically in a `finally` block. This subtle difference can lead to mistakes if someone forgets to pause Stratz.
- **Recommended action:** Consider unifying the behavior or documenting it explicitly.

---

## 7. Refactoring recommendations

1. **Create a `utils/` or `helpers/` module**
   - Move `_parse_timestamp()` there.
   - Possibly move shared top player/match logic there.

2. **Remove unused repository methods**
   - `count_by_hero()`, `list_all()` (match), `list_all_match_details()`, `list_all()` (chat wheel).

3. **Remove or implement `EXPORT_WINDOW_SECONDS`**
   - If no intended use, remove it.
   - If it was meant to filter exports by time window, implement it.

4. **Unify `TopHeroesService` and `SpecificTopService`**
   - `SpecificTopService` could become a special configuration of `TopHeroesService` rather than a duplicated class.

5. **Log parse statistics**
   - Although `parse_unparsed()` returns metrics, they are currently not consumed. Logging them explicitly would help the user.

---

## 8. Files affected by a cleanup

- `config.py` — remove `EXPORT_WINDOW_SECONDS`.
- `repositories/match_repository.py` — remove `count_by_hero()`, `list_all()`, `list_all_match_details()`.
- `repositories/chat_wheel_repository.py` — remove `list_all()`.
- `services/rampage_service.py` — replace `_parse_timestamp()` with a shared helper.
- `services/top_heroes_service.py` — replace `_parse_timestamp()` and possibly unify with `SpecificTopService`.
- `services/specific_top_service.py` — replace `_parse_timestamp()` and possibly unify with `TopHeroesService`.
- `main.py` — fix parse submenu wording.

---

## Note

The cleanups identified in this report have **not** been applied. They are documented here for future execution.
