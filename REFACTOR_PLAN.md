# Refactor Plan

> **Status: COMPLETED.** The refactor described in this plan was executed. `main.py` is now a minimal entry point; `ServiceFactory` lives in `cli/factory.py`, menus in `cli/menus.py`, shared helpers in `core/`, discovery services in `services/discovery/` (including the newer `DailyHarvestService`), replay JSON storage in `core/replay_store.py`, and the `tests/` scaffolding exists (empty, prepared for pytest). Later additions not covered here: `services/analysis_service.py`, `services/drive_service.py`, and the Google Drive flow. This file is kept for historical reference.

## 1. Diagnosis of the current architecture

The current architecture already follows a correct layered pattern:

```
api → services → repositories → database
```

However, it has the following problems:

- **Mixed responsibilities in `main.py`:** it contains the entry point, the dependency factory (`ServiceFactory`), and all interactive menu logic.
- **Duplicated code in services:** `_parse_timestamp()` exists in three files, and `TopHeroesService`/`SpecificTopService` repeat top player/match search logic.
- **No shared utilities module:** there is no place for cross-cutting helpers.
- **Accumulated dead code:** unused constants and repository methods.
- **No domain models:** everything flows as raw `dict`, making typing and validation harder.
- **No tests:** there is no test structure or clear separation for testing.

---

## 2. Proposed structure

The layered architecture is preserved, but reorganized internally for clarity:

```
.
├── main.py                              # Minimal entry point
├── config.py
├── database.py
├── requirements.txt
├── .env.example
├── data/
│   └── chat_wheel.json
├── api/
│   ├── __init__.py
│   ├── client.py                        # StratzClient
│   ├── opendota_client.py
│   └── queries.py
├── cli/
│   ├── __init__.py
│   ├── menus.py                         # show_*_menu / run_*_menu functions
│   └── factory.py                       # ServiceFactory (dependency injection)
├── core/
│   ├── __init__.py
│   ├── time.py                          # Shared _parse_timestamp()
│   └── models.py                        # Dataclasses: Hero, Match, ChatWheel, etc.
├── services/
│   ├── __init__.py
│   ├── hero_service.py
│   ├── chat_wheel_service.py
│   ├── parse_service.py
│   ├── export_service.py
│   └── discovery/
│       ├── __init__.py
│       ├── base.py                      # BaseDiscoveryService with shared helpers
│       ├── rampage_service.py
│       ├── top_heroes_service.py
│       └── specific_top_service.py
├── repositories/
│   ├── __init__.py
│   ├── hero_repository.py
│   ├── match_repository.py
│   └── chat_wheel_repository.py
└── tests/
    ├── __init__.py
    ├── test_services/
    ├── test_repositories/
    └── conftest.py
```

---

## 3. What to move

### a) `ServiceFactory` from `main.py` to `cli/factory.py`

**Reason:** `main.py` should be only the entry point. The dependency factory is wiring infrastructure and has nothing to do with menu logic.

**Advantages:**
- `main.py` becomes a reduced startup sequence + menu loop.
- The factory can be imported and reused in tests.
- Easier to change the dependency injection mechanism in the future.

### b) Menus from `main.py` to `cli/menus.py`

**Reason:** Separate the user interface (prints and `input()`) from orchestration.

**Advantages:**
- Menus can be tested in isolation by mocking `input()` and `print()`.
- `main.py` is more readable.
- New menu options are added in a single semantic place.

### c) `_parse_timestamp()` to `core/time.py`

**Reason:** Three services duplicate the same function.

**Advantages:**
- Single source of truth.
- Less risk of divergence.
- Easy to test.

### d) Discovery services to `services/discovery/`

**Reason:** Group related match discovery logic together.

**Advantages:**
- `services/` becomes organized by domain.
- Easier to understand what each service does.
- Prepares the ground for adding more discovery strategies.

---

## 4. What to separate

### a) Separate UI from DI

Currently `main.py` does three things: startup orchestration, service creation, and rendering menus.

**Proposed separation:**
- `cli/factory.py` → service creation.
- `cli/menus.py` → menus.
- `main.py` → only calls both.

### b) Separate cross-cutting helpers

Create `core/` for:
- `core/time.py` — time utilities.
- `core/models.py` — typed data models.

**Advantages:**
- Reduces cross-dependencies between services.
- Improves implicit code documentation.
- Facilitates data validation.

### c) Separate tests from source code

Create `tests/` at the root with subfolders mirroring the project structure.

**Advantages:**
- No mixing of production code and tests.
- Easy to run `pytest` from the root.

---

## 5. What to unify

### a) `TopHeroesService` and `SpecificTopService`

**Problem:** They share almost all logic: fetch top players, fetch matches, save matches.

**Option 1 (recommended):** Create `BaseDiscoveryService` with common methods `_fetch_top_players()`, `_fetch_player_matches()`, and `_save_matches()`. `TopHeroesService` and `SpecificTopService` inherit and only configure:
- How to obtain the hero list (`winWeek` vs `Config.SPECIFIC_TOP_HEROES`).
- How many top players to request per hero.

**Option 2:** Convert `SpecificTopService` into a special instance of `TopHeroesService` by passing it a custom hero map and counts.

**Advantages of unification:**
- Removes duplication.
- Less code to maintain.
- Changes to match saving logic apply in one place.

**Risk:** `SpecificTopService` uses a dynamic `take` per hero, while `TopHeroesService` uses a fixed `take`. The unification must handle this parameter flexibly to avoid losing functionality.

### b) `_parse_timestamp()` into a shared helper

See section 3.c.

---

## 6. General advantages of the refactor

| Aspect | Before | After |
|--------|--------|-------|
| `main.py` | Entry point + factory + menus | Minimal entry point |
| Helpers | Duplicated across services | Centralized in `core/` |
| Discovery | Services scattered | Grouped in `services/discovery/` |
| Typing | Excessive use of `dict` | Dataclasses in `core/models.py` |
| Tests | None | `tests/` structure prepared |
| DI | Mixed with UI | Isolated in `cli/factory.py` |
| Technical debt | Dead and duplicated code | Clean and focused |

**Additional advantages:**
- The project scales better if more data sources or menus are added.
- Unit tests become easier to write.
- New developers understand the structure faster.

---

## 7. Risks

### Risk 1: Import changes

Moving files between folders breaks existing imports. If not all `from ... import ...` statements are updated correctly, the application will stop working.

**Mitigation:**
- Migrate step by step.
- After each move, run `python main.py` to validate.
- Use `python -m py_compile` on all files.

### Risk 2: Behavior loss during unification

Unifying `TopHeroesService` and `SpecificTopService` can introduce bugs if the dynamic `take` parameter is not handled correctly.

**Mitigation:**
- First extract shared helpers without changing logic.
- Then refactor one class at a time.
- Compare output before and after with the same dataset.

### Risk 3: Over-engineering

The project is small. Moving everything into many subfolders could make it harder to navigate rather than easier.

**Mitigation:**
- Keep only necessary abstractions.
- Do not introduce unnecessary abstract interfaces.
- If a unification complicates more than it simplifies, keep the services separate but with shared helpers.

### Risk 4: New tests touching real data

If tests are added, there is a risk they touch the real database or external APIs.

**Mitigation:**
- Use SQLite `:memory:` for repository tests.
- Mock `StratzClient` and `OpenDotaClient` in service tests.
- Never run tests against the real `data.db`.

### Risk 5: Outdated documentation

After moving files, existing docs in `docs/modules/` reference old paths.

**Mitigation:**
- Update `docs/modules/*.md` after the refactor.
- Regenerate or adjust `README.md` if the folder structure changes.

---

## 8. Recommended execution order

1. **Step 0:** Apply `CLEANUP_REPORT.md` first (remove dead code).
2. **Step 1:** Create `core/time.py` and replace `_parse_timestamp()` in the three services.
3. **Step 2:** Extract `ServiceFactory` to `cli/factory.py`.
4. **Step 3:** Extract menus to `cli/menus.py`.
5. **Step 4:** Create `services/discovery/` and move discovery services there.
6. **Step 5:** Unify `TopHeroesService` and `SpecificTopService` via `BaseDiscoveryService`.
7. **Step 6:** Create `core/models.py` and type key structures.
8. **Step 7:** Create `tests/` structure with initial tests.
9. **Step 8:** Update documentation.

---

## Note

The refactor actions described in this plan **have been applied** (see the status banner at the top). This document is kept for historical reference.
