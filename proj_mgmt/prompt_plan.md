# Elite Minor Hockey Coach App — Build Blueprint (based on `spec.md`)

## 0) What we’re building (at a glance)
- Local FastAPI app with SQLite/SQLModel, Jinja+Bootstrap UI, SortableJS drag-and-drop, WeasyPrint PDF.  
- MVP modules: **Roster** and **Lineup Builder**, plus **backup/restore**.  
- Single team active per session; simple CSV import/export; warnings for duplicates & non-active players.

---

## 1) System blueprint (end-to-end)

### 1.1 Foundations
- **Repo & Tooling:** uv, ruff, mypy, pytest, pre-commit; `.editorconfig`; `pyproject.toml`.
- **App Skeleton:** `app/` (FastAPI factory, routers), `services/`, `templates/`, `static/`, `tests/`.
- **Config:** typed settings, paths, and WeasyPrint deps discovery.
- **DB:** SQLModel models + Alembic (optional) or auto-create on first run.

### 1.2 Core domain
- **Models:** `Team`, `Player`, `LineupTemplate`, `LineupSlot` with enums & constraints.
- **Services:**  
  - `roster_service`: CRUD, CSV import/export with validation + issue report.  
  - `lineup_service`: seed slots, assign/move players, validations & warnings.  
  - `pdf_service`: render lineup → HTML → PDF.  
  - `backup_service`: timestamped copy/restore DB.

### 1.3 Web layer
- **Routers:** `/api/teams`, `/api/players`, `/api/lineups`, `/api/misc`.
- **UI:**  
  - Team selector → Dashboard quick actions.  
  - Roster list + modal add/edit; CSV import flow with result summary.  
  - Lineup builder with SortableJS boards; save & export buttons.
- **Templates:** `base.html`, `dashboard.html`, `roster_list.html`, `player_form.html`, `lineup_builder.html`, `pdf_lineup.html`.

### 1.4 Non-functional & QA
- **Validation & Errors:** 400/404/409/422/500 patterns, service exceptions → API Problem JSON.  
- **Testing:** unit (validators/services), integration (DB + routers), E2E happy path.  
- **Packaging:** run locally via `uvicorn app.main:app --reload`; optional PyInstaller later.

---

## 2) Iterative plan → chunks → right-sized steps

### Milestone A — Scaffolding & DB
- **Chunk A1:** Repo & quality gates  
- **Chunk A2:** App factory, config, DB engine  
- **Chunk A3:** Domain models & initial migration/auto-create  
- **Chunk A4:** Seed minimal data & healthcheck route

### Milestone B — Teams & Roster API
- **Chunk B1:** Teams API (list/create/get)  
- **Chunk B2:** Players API (team-scoped CRUD)  
- **Chunk B3:** Validation utilities & error mapping

### Milestone C — Roster UI + CSV
- **Chunk C1:** Jinja pages for team selector & roster list  
- **Chunk C2:** Modal add/edit player  
- **Chunk C3:** CSV import/export service + UI

### Milestone D — Lineup Builder
- **Chunk D1:** Lineup data model service  
- **Chunk D2:** Builder UI with SortableJS  
- **Chunk D3:** Save/Load templates and warnings

### Milestone E — PDF & Backup
- **Chunk E1:** PDF template + service  
- **Chunk E2:** Backup/restore endpoints & UI affordance

### Milestone F — Tests & Polish
- **Chunk F1:** Unit tests (validators, CSV, lineup)  
- **Chunk F2:** Integration tests (API + DB)  
- **Chunk F3:** E2E happy path + UX nits

---

## 3) Code-Generation LLM — Stepwise Prompts

Each section is a prompt you can hand to a code-generation model. Run them **in order**.

---

### A — Scaffolding & DB

#### A1.1 — Repo & tooling
You are a senior Python engineer. Implement repo scaffolding for a FastAPI app.

Goal:
- Create a Python 3.12 project with FastAPI, SQLModel, Jinja2, WeasyPrint, Uvicorn.
- Add ruff, mypy, pytest, pre-commit, .editorconfig.

Actions:
1) Create pyproject.toml with deps:
   fastapi, uvicorn[standard], sqlmodel, jinja2, python-multipart, weasyprint, pydantic-settings, httpx, pytest, pytest-asyncio, ruff, mypy, types-setuptools.
2) Add ruff & mypy configs (strict but practical), pytest.ini, .editorconfig.
3) Add .pre-commit-config.yaml for ruff/mypy/black and enable hooks.
4) Create README with run instructions.
5) Add minimal src tree: app/, services/, routers/, templates/, static/{css,js}, utils/, tests/{unit,integration,e2e}.

Acceptance:
- `uv run pytest` executes (0 tests OK).
- `uv run ruff check` & `mypy` pass.
- README shows local run command.

#### A1.2 - CI Workflow
Add GitHub Actions workflow `.github/workflows/ci.yml` to run ruff, mypy, pytest on pushes/PRs to main.

Acceptance:
- Workflow YAML references Python 3.12 and uses uv (or pip) to install and cache deps.

A2.1 — App factory & config
Create `app/main.py` with FastAPI factory and health router stub. Create `app/config.py` with typed settings (data_dir, db_path), defaulting to `~/.coach_app/data.db`.

Acceptance:
- `uvicorn app.main:app --reload` boots and GET `/api/health` returns `{"status":"ok"}`.

#### A2.2 — DB engine & session
Implement `app/db.py`:
- SQLModel engine bound to `Settings.db_path`.
- Session dependency `get_session()`.

Acceptance:
- Importing `get_session` works; no runtime errors.

#### A3.1 — Domain models
Implement `app/models.py` using SQLModel:
- Team(id, name, season, created_at), unique(name, season).
- Player(id, team_id FK, name, position Enum[F,D,G], jersey 1-99 nullable, hand Enum[L,R] nullable, birthdate/date nullable, email/phone nullable, status Enum[Active, Affiliate, Injured, Inactive], created_at).
- LineupTemplate(id, team_id FK, name, notes, date_saved, created_at).
- LineupSlot(id, template_id FK, slot_type Enum[FWD, DEF, G], slot_label str, order_index int, player_id FK nullable).

Acceptance:
- `sqlmodel.SQLModel.metadata.create_all(engine)` succeeds.
- Enum values match spec.

#### A3.2 — DB init on startup 
In `app/main.py`, on startup event, call create_all(engine). No Alembic yet.

Acceptance:
- First boot creates DB file at configured path.

#### A4.1 — Health & smoke tests
Add `tests/integration/test_health.py`: start app via TestClient, assert 200/{"status":"ok"}.

Acceptance:
- pytest shows 1 passing test.

### B — Teams & Players API

#### B1.1 — Teams endpoints
Create `schemas.py` (Pydantic) for TeamIn(name, season), TeamOut. Implement `routers/teams.py`:
- GET /api/teams (list)
- POST /api/teams (create with unique name+season)
- GET /api/teams/{id}

Acceptance:
- Integration tests for list/create/get; 409 on duplicate (name,season).

#### B2.1 — Players list/create
Create `routers/players.py`:
- GET /api/teams/{team_id}/players with filters (position, hand, birth_year) & sorts (year, jersey, position, name).
- POST /api/teams/{team_id}/players with required (name, position) and optional fields.

Acceptance:
- Tests: create valid player; 422 invalid enums; list supports filters/sorts.

#### B2.2 — Players update/delete
Extend `routers/players.py`:
- PUT /api/players/{id}
- DELETE /api/players/{id}

Acceptance:
- Tests for update fields and delete; 404 when not found.

#### B3.1 — Validators & errors
Implement `utils/validators.py` for jersey range, ISO date parsing; `utils/errors.py` with ServiceError → HTTPException mapping. Refactor routers to use these helpers.

Acceptance:
- Unit tests for validator edge cases; HTTP codes match spec (400/404/409/422).

### C — Roster UI & CSV

#### C1.1 — Base & Dashboard
Create `templates/base.html` (Bootstrap, nav) and `templates/dashboard.html` with quick actions (Add Player, Manage Roster, Create Lineup, Load Lineup). Add `/` route rendering dashboard and team selector.

Acceptance:
- Manual: page renders; links present.

#### C1.2 — Roster list page
Create `templates/roster_list.html` with table columns per spec and status chips. Router for `/teams/{team_id}/roster` that fetches data from API.

Acceptance:
- Manual: list renders; empty-state message shown when no players.

#### C2.1 — Modal add/edit player
Implement `templates/player_form.html` as modal. Add POST handlers to call API, then redirect back. Show flash/toast on success.

Acceptance:
- Manual: can add/edit player; invalid inputs show inline errors.

#### C3.1 — CSV service
Create `services/csv_service.py`:
- Import: accept headers [name,position,jersey,hand,birthdate,email,phone,status], clear invalid → issues list; allow duplicates but flag; return (created_count, issues_csv_path).
- Export: return CSV with same headers.

Acceptance:
- Unit tests with malformed rows, missing optionals, dupes flagged.

#### C3.2 — CSV endpoints & UI
Add to `routers/players.py`:
- POST /api/teams/{team_id}/players/import_csv (multipart)
- GET  /api/teams/{team_id}/players/export_csv

UI: Upload form + result card showing counts and link to issues CSV.

Acceptance:
- Integration tests for endpoints; manual import/export works.

### D — Lineup Builder

#### D1.1 — Seed slots
`services/lineup_service.py`:
- Function to seed fixed slots per spec: 4 FWD lines (LW/C/RW), 3 DEF pairs (L/R), 2 goalies.
- Create LineupTemplate with seeded LineupSlots.

Acceptance:
- Unit test: correct count and labels created in order.

#### D1.2 — Assign/move with warnings
Add functions:
- assign_player_to_slot(template_id, slot_id, player_id)
- validations: player.team_id matches; track duplicates; warn if player.status != Active.

Acceptance:
- Unit tests cover dup and status warnings; no DB integrity break.

#### D2.1 — Builder UI
Create `templates/lineup_builder.html`:
- Left pane: available players list (card with name, jersey, position, status tag; non-Active visually flagged).
- Right pane: slot columns using data-slot-id.

Acceptance:
- Manual: board renders from template data.

#### D2.2 — Drag & drop behavior
Add `static/js/lineup.js` using SortableJS:
- Drag from available → slot; slot → slot; slot → available.
- On drop, call API to update assignment; display warning banner if any.

Acceptance:
- Manual: can move players; banner shows duplicate/non-Active warnings.

#### D3.1 — Lineup APIs
In `routers/lineups.py`:
- GET /api/teams/{team_id}/lineups (list)
- POST /api/teams/{team_id}/lineups (create; seeds slots)
- GET /api/lineups/{template_id} (detail including slots+players)

Acceptance:
- Integration tests for create/list/get.

#### D3.2 — Save & warnings
Add:
- PUT /api/lineups/{template_id}/slots (bulk update from UI)
- POST /api/lineups/{template_id}/save (sets date_saved)

Acceptance:
- date_saved populated; warnings returned in response metadata.

### E — PDF & Backup

#### E1.1 — PDF template
Create `templates/pdf_lineup.html` with print CSS:
- Header (team, season, template name, date).
- Sections: Forwards (FWD1–4), Defense (DEF1–3), Goalies (Starter/Backup).
- Only on-ice slots included.

Acceptance:
- Visual check in browser print preview (HTML).

#### E1.2 — PDF service & route
`services/pdf_service.py` render HTML → PDF via WeasyPrint.
`GET /api/lineups/{template_id}/export_pdf` returns file.

Acceptance:
- Integration test verifies content-type and non-empty bytes.

#### E2.1 — Backup/restore
`services/backup_service.py`:
- GET /api/backup: stream copy of DB with timestamped name.
- POST /api/restore: accept DB file; replace current (with safety check).

Acceptance:
- Integration: backup returns file; restore swaps DB then healthcheck OK.

#### E2.2 — UI buttons
Add dashboard buttons for Backup/Restore, with confirmation dialogs.

Acceptance:
- Manual: backup downloads; restore shows success message.

### F — Tests & Polish

#### F1.1 — Unit tests roundup
Add missing unit tests for validators, csv_service, lineup_service.

Acceptance:
- >90% coverage in services; green CI.

#### F2.1 — Integration tests roundup
API tests for teams, players, lineups, pdf, backup using temp DB.

Acceptance:
- All pass in CI on Linux/macOS.

#### F3.1 — E2E happy path
E2E: create team → add players → import CSV → build lineup → save → export PDF.

Acceptance:
- Scripted test succeeds; artifacts saved to /tmp for inspection.

#### F3.2 — UX nits
Add toasts for “Saved” & “Imported”; disable buttons while pending; empty states for pages.

Acceptance:
- Manual check on all pages.

### Final wiring checklist
    - Nav links land on live pages.
    - Every API is consumed by UI or tests.
    - PDF export works for saved template.
    - Backup/restore functions from UI.
    - Lint, type-check, and tests green.