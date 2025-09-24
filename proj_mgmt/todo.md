# TODO — Elite Minor Hockey Coach App
_Updated: 2025-09-23_

> Use this as a living checklist. Work top-to-bottom; each step is small, safe, and builds on the last. No orphan code.
**Details related to each step can be found in prompt_plan.md and spec.md**
---

## 0) Bootstrap & Housekeeping
- [x] Create a new private repo and push an empty `main` branch
- [x] Decide Python version (>=3.11) and install **uv**
- [x] Enable branch protection on `main` (PRs required, status checks required)

---

## Milestone A — Scaffolding & Database
### A1 — Repo & Quality Gates
- [x] A1.1: Initialize project + toolchain
  - [x] Add `pyproject.toml` with deps: fastapi, uvicorn[standard], sqlmodel, jinja2, python-multipart, weasyprint, pydantic-settings, httpx, pytest, pytest-asyncio, ruff, mypy
  - [x] Add dev tooling: black (optional), pre-commit, types-setuptools
  - [x] Create skeleton dirs: `app/`, `routers/`, `services/`, `utils/`, `templates/`, `static/css`, `static/js`, `tests/unit`, `tests/integration`, `tests/e2e`
  - [x] Add configs: `.editorconfig`, `pytest.ini`, `ruff.toml`, `mypy.ini`, `.pre-commit-config.yaml`
  - [x] Add `README.md` with run/test instructions
  - [x] ✅ DoD: `uv run ruff check` passes; `uv run mypy` passes; `uv run pytest` runs with 0 tests
- [x] A1.2: CI pipeline
  - [x] Create `.github/workflows/ci.yml` to run ruff, mypy, pytest on push/PR
  - [x] Cache deps; matrix Python 3.12 (and optional 3.11)
  - [x] ✅ DoD: CI succeeds on initial commit

### A2 — App Factory & Config
- [x] A2.1: App factory and health
  - [x] `app/main.py` FastAPI factory; mount routers stub; `/api/health` route → `{"status":"ok"}`
  - [x] `app/config.py` `Settings` using pydantic-settings (data_dir, db_path defaults to `~/.coach_app/data.db`)
  - [x] ✅ DoD: `uvicorn app.main:app --reload` boots; GET `/api/health` returns 200 OK
- [x] A2.2: DB engine/session
  - [x] `app/db.py` SQLModel engine from `Settings.db_path`
  - [x] `get_session()` dependency for routers/services
  - [x] ✅ DoD: Importing dependency works; no runtime errors

### A3 — Domain Models
- [x] A3.1: Define SQLModel models in `app/models.py`
  - [x] Team(id, name, season, created_at), unique(name, season)
  - [x] Player(id, team_id FK, name, position Enum[F,D,G], jersey 1–99 nullable, hand Enum[L,R] nullable, birthdate, email, phone, status Enum[Active, Affiliate, Injured, Inactive], created_at)
  - [x] LineupTemplate(id, team_id FK, name, notes, date_saved, created_at)
  - [x] LineupSlot(id, template_id FK, slot_type Enum[FWD, DEF, G], slot_label, order_index, player_id FK nullable)
  - [x] ✅ DoD: `SQLModel.metadata.create_all(engine)` succeeds
- [x] A3.2: Startup DB init
  - [x] On startup event, call `create_all(engine)` (Alembic deferred)
  - [x] ✅ DoD: First run creates DB file at `Settings.db_path`

### A4 — Smoke Tests
- [x] A4.1: Add `tests/integration/test_health.py`
  - [x] TestClient GET `/api/health` == 200 with `{"status":"ok"}`
  - [x] ✅ DoD: Test passes locally and in CI

---

## Milestone B — Teams & Players API
### B1 — Teams
- [x] B1.1: `schemas.py` TeamIn/TeamOut
- [x] B1.2: `routers/teams.py`
  - [x] GET `/api/teams` (list)
  - [x] POST `/api/teams` (create; unique name+season)
  - [x] GET `/api/teams/{id}` (detail)
  - [x] ✅ DoD: Integration tests cover happy path + 409 duplicate

### B2 — Players
- [x] B2.1: `routers/players.py` list/create
  - [x] GET `/api/teams/{team_id}/players` with filters (position, hand, birth_year) & sorts (name, position, jersey)
  - [x] POST `/api/teams/{team_id}/players` with required (name, position), optional others
  - [x] ✅ DoD: 422 invalid enums; list filters work
- [x] B2.2: Update/delete
  - [x] PUT `/api/players/{id}` (partial/full)
  - [x] DELETE `/api/players/{id}`
  - [x] ✅ DoD: 404 when not found; tests pass

### B3 — Validation & Error Mapping
- [x] B3.1: `utils/validators.py` (jersey range, ISO date) + unit tests
- [x] B3.2: `utils/errors.py` ServiceError → HTTPException mapping
- [x] B3.3: Refactor routers to use helpers
- [x] ✅ DoD: Correct status codes: 400/404/409/422; tests green

---

## Milestone C — Roster UI & CSV
### C1 — Base UI & Dashboard
- [x] C1.1: `templates/base.html` (Bootstrap), navbar
- [x] C1.2: `templates/dashboard.html` with quick actions
- [x] C1.3: `/` route renders dashboard and team selector
- [x] ✅ DoD: Pages render; links work

### C2 — Roster Pages
- [x] C2.1: `templates/roster_list.html` (table, filters, status chips)
- [x] C2.2: `templates/player_form.html` modal add/edit
- [x] C2.3: Flash/toast on success; inline validation errors
- [x] ✅ DoD: Manual: add/edit works; bad inputs show errors

### C3 — CSV Import/Export
- [x] C3.1: `services/csv_service.py`
  - [x] Import headers: name, position, jersey, hand, birthdate, email, phone, status
  - [x] Clear invalid → issues list (row, field, reason)
  - [x] Allow duplicates but flag; return counts + issues CSV path
  - [x] Export same headers
  - [x] ✅ DoD: Unit tests for malformed rows, missing optionals, dupes flagged
- [x] C3.2: Endpoints & UI
  - [x] POST `/api/teams/{team_id}/players/import_csv` (multipart)
  - [x] GET `/api/teams/{team_id}/players/export_csv`
  - [x] Upload form + result card (counts + link to issues CSV)
  - [x] ✅ DoD: Integration tests; manual import/export works

---

## Milestone D — Lineup Builder
### D1 — Data & Services
- [x] D1.1: `services/lineup_service.py` seed slots
  - [x] 4 forward lines (LW/C/RW), 3 D pairs (L/R), 2 G (Starter/Backup)
  - [x] ✅ DoD: Unit test confirms counts & labels
- [x] D1.2: Assignment/move & warnings
  - [x] `assign_player_to_slot` with validations (team match)
  - [x] Warn on duplicates; warn on non-Active status
  - [x] ✅ DoD: Unit tests for dup/status warnings

### D2 — Builder UI
- [x] D2.1: `templates/lineup_builder.html` two-pane layout
  - [x] Left: available players (card shows name, jersey, position, status)
  - [x] Right: slot boards (data-slot-id, ordered)
- [x] D2.2: `static/js/lineup.js` (SortableJS)
  - [x] Drag from available → slot; slot ↔ slot; slot → available
  - [x] On drop: call API; show warning banner (dup/non-Active)
  - [x] ✅ DoD: Manual drag works; warnings visible

### D3 — Lineup API
- [x] D3.1: `routers/lineups.py`
  - [x] GET `/api/teams/{team_id}/lineups` (list)
  - [x] POST `/api/teams/{team_id}/lineups` (create; seeds slots)
  - [x] GET `/api/lineups/{template_id}` (detail including slots+players)
- [x] D3.2: Save & bulk updates
  - [x] PUT `/api/lineups/{template_id}/slots` (bulk update)
  - [x] POST `/api/lineups/{template_id}/save` (sets `date_saved`)
  - [x] ✅ DoD: date_saved set; warnings returned in response meta

---

## Milestone E — PDF & Backup
### E1 — PDF Export
- [x] E1.1: `templates/pdf_lineup.html` with print CSS
  - [x] Header: team, season, template name, date
  - [x] Sections: Forwards (FWD1–4), Defense (DEF1–3), Goalies (Starter/Backup)
  - [x] Only on-ice slots included
- [x] E1.2: `services/pdf_service.py` + route
  - [x] GET `/api/lineups/{template_id}/export_pdf` returns PDF
  - [x] ✅ DoD: Integration test checks content-type and bytes > 0

### E2 — Backup/Restore
- [x] E2.1: `services/backup_service.py`
  - [x] GET `/api/backup` returns timestamped DB copy
  - [x] POST `/api/restore` accepts DB file, safe replace
- [x] E2.2: UI buttons with confirmations
  - [x] Dashboard buttons (Backup, Restore)
  - [x] ✅ DoD: Manual: backup downloads; restore succeeds; health OK

---

## Milestone F — Tests & Polish
### F1 — Unit Tests
- [ ] F1.1: Cover validators, csv_service, lineup_service edge cases
- [ ] F1.2: Aim for >90% services coverage
- [ ] ✅ DoD: Coverage threshold met

### F2 — Integration Tests
- [ ] F2.1: Teams/Players/Lineups/PDF/Backup using temp DB
- [ ] F2.2: CI runs tests on Linux/macOS
- [ ] ✅ DoD: Green CI

### F3 — E2E Happy Path & UX
- [ ] F3.1: Script E2E: create team → add players → import CSV → build lineup → save → export PDF
- [ ] F3.2: UX polish
  - [ ] Toasts for “Saved” & “Imported”
  - [ ] Disable buttons while pending
  - [ ] Empty states for roster and lineups
- [ ] ✅ DoD: Manual checks pass

---

## Final Wiring Checklist
- [ ] All nav links land on live pages
- [ ] Every API used by UI and/or tests (no orphans)
- [ ] PDF export works for a saved template
- [ ] Backup/restore usable from UI
- [ ] Lint, type-check, and tests green

---

## Backlog / Nice-to-Haves (Optional)
- [ ] Move to Alembic migrations
- [ ] Role-based auth (coach-only local auth)
- [ ] PyInstaller/Briefcase packaging
- [ ] Dark mode + improved theming
- [ ] Inline roster CSV mapping (flex headers)
- [ ] Undo/redo in lineup builder

---

## Operational Notes
- [ ] Keep PRs to one conceptual change
- [ ] Each step compiles, runs, and/or has tests
- [ ] Update README as features land
- [ ] Tag releases at the end of each milestone

---

## Part B Code Review & Fixes (2025-01-27)

### Issues Found and Fixed:
1. **Linting Errors (72 → 0)**: Fixed all ruff linting errors including:
   - Import organization and sorting
   - Type annotations (Optional[X] → X | None, List[X] → list[X])
   - Unused imports removal
   - Exception chaining with `raise ... from err`
   - Line length issues

2. **Type Checking Errors (8 → 0)**: Fixed all mypy errors including:
   - Module resolution issues by adding missing `__init__.py` files
   - Return type compatibility (Sequence → list conversion)
   - SQLModel field type handling for sorting and filtering
   - Proper type annotations for dynamic field selection

3. **Configuration Updates**:
   - Updated `ruff.toml` to ignore B008 (FastAPI Depends() usage) and E402 (test path setup)
   - All linting and type checking now passes

4. **Code Quality Improvements**:
   - Added proper exception chaining throughout the codebase
   - Fixed import organization across all files
   - Updated to modern Python type annotations
   - Ensured all tests continue to pass (7/7 tests passing)

### Files Modified:
- `app/main.py` - Import organization
- `app/models.py` - Removed unused imports
- `app/schemas.py` - Updated type annotations
- `routers/teams.py` - Fixed imports, types, and return values
- `routers/players.py` - Fixed imports, types, exception handling, and SQL queries
- `utils/errors.py` - Updated type annotations and exception chaining
- `utils/validators.py` - Added proper exception chaining
- `tests/integration/test_teams.py` - Fixed import organization
- `ruff.toml` - Added ignore rules for FastAPI-specific patterns
- Added missing `__init__.py` files in `routers/`, `utils/`, and `services/`

### Status: ✅ All 36 errors and 77 warnings have been addressed
- Ruff check: ✅ All checks passed!
- MyPy check: ✅ Success: no issues found in 15 source files
- Tests: ✅ 7 passed in 1.19s