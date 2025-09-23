# TODO — Elite Minor Hockey Coach App
_Updated: 2025-09-23_

> Use this as a living checklist. Work top-to-bottom; each step is small, safe, and builds on the last. No orphan code.
**Details related to each step can be found in prompt_plan.md and spec.md**
---

## 0) Bootstrap & Housekeeping
- [x] Create a new private repo and push an empty `main` branch
- [ ] Decide Python version (>=3.11) and install **uv**
- [ ] Enable branch protection on `main` (PRs required, status checks required)
- [ ] Add a project board with Milestones A–F

---

## Milestone A — Scaffolding & Database
### A1 — Repo & Quality Gates
- [ ] A1.1: Initialize project + toolchain
  - [ ] Add `pyproject.toml` with deps: fastapi, uvicorn[standard], sqlmodel, jinja2, python-multipart, weasyprint, pydantic-settings, httpx, pytest, pytest-asyncio, ruff, mypy
  - [ ] Add dev tooling: black (optional), pre-commit, types-setuptools
  - [ ] Create skeleton dirs: `app/`, `routers/`, `services/`, `utils/`, `templates/`, `static/css`, `static/js`, `tests/unit`, `tests/integration`, `tests/e2e`
  - [ ] Add configs: `.editorconfig`, `pytest.ini`, `ruff.toml`, `mypy.ini`, `.pre-commit-config.yaml`
  - [ ] Add `README.md` with run/test instructions
  - [ ] ✅ DoD: `uv run ruff check` passes; `uv run mypy` passes; `uv run pytest` runs with 0 tests
- [ ] A1.2: CI pipeline
  - [ ] Create `.github/workflows/ci.yml` to run ruff, mypy, pytest on push/PR
  - [ ] Cache deps; matrix Python 3.12 (and optional 3.11)
  - [ ] ✅ DoD: CI succeeds on initial commit

### A2 — App Factory & Config
- [ ] A2.1: App factory and health
  - [ ] `app/main.py` FastAPI factory; mount routers stub; `/api/health` route → `{"status":"ok"}`
  - [ ] `app/config.py` `Settings` using pydantic-settings (data_dir, db_path defaults to `~/.coach_app/data.db`)
  - [ ] ✅ DoD: `uvicorn app.main:app --reload` boots; GET `/api/health` returns 200 OK
- [ ] A2.2: DB engine/session
  - [ ] `app/db.py` SQLModel engine from `Settings.db_path`
  - [ ] `get_session()` dependency for routers/services
  - [ ] ✅ DoD: Importing dependency works; no runtime errors

### A3 — Domain Models
- [ ] A3.1: Define SQLModel models in `app/models.py`
  - [ ] Team(id, name, season, created_at), unique(name, season)
  - [ ] Player(id, team_id FK, name, position Enum[F,D,G], jersey 1–99 nullable, hand Enum[L,R] nullable, birthdate, email, phone, status Enum[Active, Affiliate, Injured, Inactive], created_at)
  - [ ] LineupTemplate(id, team_id FK, name, notes, date_saved, created_at)
  - [ ] LineupSlot(id, template_id FK, slot_type Enum[FWD, DEF, G], slot_label, order_index, player_id FK nullable)
  - [ ] ✅ DoD: `SQLModel.metadata.create_all(engine)` succeeds
- [ ] A3.2: Startup DB init
  - [ ] On startup event, call `create_all(engine)` (Alembic deferred)
  - [ ] ✅ DoD: First run creates DB file at `Settings.db_path`

### A4 — Smoke Tests
- [ ] A4.1: Add `tests/integration/test_health.py`
  - [ ] TestClient GET `/api/health` == 200 with `{"status":"ok"}`
  - [ ] ✅ DoD: Test passes locally and in CI

---

## Milestone B — Teams & Players API
### B1 — Teams
- [ ] B1.1: `schemas.py` TeamIn/TeamOut
- [ ] B1.2: `routers/teams.py`
  - [ ] GET `/api/teams` (list)
  - [ ] POST `/api/teams` (create; unique name+season)
  - [ ] GET `/api/teams/{id}` (detail)
  - [ ] ✅ DoD: Integration tests cover happy path + 409 duplicate

### B2 — Players
- [ ] B2.1: `routers/players.py` list/create
  - [ ] GET `/api/teams/{team_id}/players` with filters (position, hand, birth_year) & sorts (name, position, jersey)
  - [ ] POST `/api/teams/{team_id}/players` with required (name, position), optional others
  - [ ] ✅ DoD: 422 invalid enums; list filters work
- [ ] B2.2: Update/delete
  - [ ] PUT `/api/players/{id}` (partial/full)
  - [ ] DELETE `/api/players/{id}`
  - [ ] ✅ DoD: 404 when not found; tests pass

### B3 — Validation & Error Mapping
- [ ] B3.1: `utils/validators.py` (jersey range, ISO date) + unit tests
- [ ] B3.2: `utils/errors.py` ServiceError → HTTPException mapping
- [ ] B3.3: Refactor routers to use helpers
- [ ] ✅ DoD: Correct status codes: 400/404/409/422; tests green

---

## Milestone C — Roster UI & CSV
### C1 — Base UI & Dashboard
- [ ] C1.1: `templates/base.html` (Bootstrap), navbar
- [ ] C1.2: `templates/dashboard.html` with quick actions
- [ ] C1.3: `/` route renders dashboard and team selector
- [ ] ✅ DoD: Pages render; links work

### C2 — Roster Pages
- [ ] C2.1: `templates/roster_list.html` (table, filters, status chips)
- [ ] C2.2: `templates/player_form.html` modal add/edit
- [ ] C2.3: Flash/toast on success; inline validation errors
- [ ] ✅ DoD: Manual: add/edit works; bad inputs show errors

### C3 — CSV Import/Export
- [ ] C3.1: `services/csv_service.py`
  - [ ] Import headers: name, position, jersey, hand, birthdate, email, phone, status
  - [ ] Clear invalid → issues list (row, field, reason)
  - [ ] Allow duplicates but flag; return counts + issues CSV path
  - [ ] Export same headers
  - [ ] ✅ DoD: Unit tests for malformed rows, missing optionals, dupes flagged
- [ ] C3.2: Endpoints & UI
  - [ ] POST `/api/teams/{team_id}/players/import_csv` (multipart)
  - [ ] GET `/api/teams/{team_id}/players/export_csv`
  - [ ] Upload form + result card (counts + link to issues CSV)
  - [ ] ✅ DoD: Integration tests; manual import/export works

---

## Milestone D — Lineup Builder
### D1 — Data & Services
- [ ] D1.1: `services/lineup_service.py` seed slots
  - [ ] 4 forward lines (LW/C/RW), 3 D pairs (L/R), 2 G (Starter/Backup)
  - [ ] ✅ DoD: Unit test confirms counts & labels
- [ ] D1.2: Assignment/move & warnings
  - [ ] `assign_player_to_slot` with validations (team match)
  - [ ] Warn on duplicates; warn on non-Active status
  - [ ] ✅ DoD: Unit tests for dup/status warnings

### D2 — Builder UI
- [ ] D2.1: `templates/lineup_builder.html` two-pane layout
  - [ ] Left: available players (card shows name, jersey, position, status)
  - [ ] Right: slot boards (data-slot-id, ordered)
- [ ] D2.2: `static/js/lineup.js` (SortableJS)
  - [ ] Drag from available → slot; slot ↔ slot; slot → available
  - [ ] On drop: call API; show warning banner (dup/non-Active)
  - [ ] ✅ DoD: Manual drag works; warnings visible

### D3 — Lineup API
- [ ] D3.1: `routers/lineups.py`
  - [ ] GET `/api/teams/{team_id}/lineups` (list)
  - [ ] POST `/api/teams/{team_id}/lineups` (create; seeds slots)
  - [ ] GET `/api/lineups/{template_id}` (detail including slots+players)
- [ ] D3.2: Save & bulk updates
  - [ ] PUT `/api/lineups/{template_id}/slots` (bulk update)
  - [ ] POST `/api/lineups/{template_id}/save` (sets `date_saved`)
  - [ ] ✅ DoD: date_saved set; warnings returned in response meta

---

## Milestone E — PDF & Backup
### E1 — PDF Export
- [ ] E1.1: `templates/pdf_lineup.html` with print CSS
  - [ ] Header: team, season, template name, date
  - [ ] Sections: Forwards (FWD1–4), Defense (DEF1–3), Goalies (Starter/Backup)
  - [ ] Only on-ice slots included
- [ ] E1.2: `services/pdf_service.py` + route
  - [ ] GET `/api/lineups/{template_id}/export_pdf` returns PDF
  - [ ] ✅ DoD: Integration test checks content-type and bytes > 0

### E2 — Backup/Restore
- [ ] E2.1: `services/backup_service.py`
  - [ ] GET `/api/backup` returns timestamped DB copy
  - [ ] POST `/api/restore` accepts DB file, safe replace
- [ ] E2.2: UI buttons with confirmations
  - [ ] Dashboard buttons (Backup, Restore)
  - [ ] ✅ DoD: Manual: backup downloads; restore succeeds; health OK

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
