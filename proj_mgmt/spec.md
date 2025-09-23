# Elite Minor Hockey Coach App — MVP Technical Specification

## 1) Vision & Scope (MVP)
A **local web app** (runs on `localhost`) that lets a coach manage a single team per session: roster, statuses, and **drag-and-drop lineup templates**. Export lineups to **lightly-formatted PDFs**. Archive/load teams via in-app menu. Simple backups to a local file. Single-user, open access on personal machine.

### Core MVP Modules
1. **Roster Management**
2. **Lineup Builder (Templates, no Games yet)**

Future-ready placeholders: player profiles (notes/goals), roles, schedule, attendance.

---

## 2) Architecture & Tech Choices

### Runtime
- **Local web app** served via `uvicorn`, opened in browser.

### Backend
- **FastAPI** (async, type-hinted, clean JSON APIs)
- **SQLModel** ORM on **SQLite** DB (single file on disk)
- Templating/UI: **Jinja** + **Bootstrap** (moderately styled)
- Drag-and-Drop: **SortableJS**
- PDF generation: **WeasyPrint** (HTML + print CSS → PDF)

### Packaging / Run
- Dev: `uvicorn app.main:app --reload`
- Optional later: PyInstaller (single executable)

### Project Structure
app/
--- main.py # FastAPI app factory & routes include
--- config.py       # paths, settings
--- db.py           # engine/session init
--- models.py       # SQLModel tables & enums
--- schemas.py      # Pydantic models
services/
--- roster_service.py
--- lineup_service.py
--- backup_service.py
--- pdf_service.py
--- csv_service.py
routers/
--- teams.py
--- players.py
--- lineups.py
--- misc.py
templates/
--- base.html
--- dashboard.html
--- roster_list.html
--- player_form.html
--- lineup_builder.html
--- pdf_lineup.html
static/
--- css/
--- js/
utils/
--- validators.py
--- errors.py
tests/
--- unit/
--- integration/
--- e2e/


---

## 3) Data Model (SQLite via SQLModel)

### Team
- `id` (PK)
- `name` (str)
- `season` (str) — **unique with `name`**
- `created_at` (datetime)

### Player
- `id` (PK)
- `team_id` (list, FK→Team) # a player could be on multiple teams at some point
- `name` (str, required)
- `position` (enum: F/D/G, required)
- `jersey` (int, 1–99, nullable)
- `hand` (enum: L/R, nullable)
- `birthdate` (date, nullable)
- `email` (str, nullable)
- `phone` (str, nullable)
- `status` (enum: Active (default), Affiliate, Injured, Inactive)
- `created_at` (datetime)

### LineupTemplate
- `id` (PK)
- `team_id` (FK→Team)
- `name` (str, required)
- `notes` (str, nullable)
- `date_saved` (date/datetime)
- `created_at` (datetime)

### LineupSlot
- `id` (PK)
- `template_id` (FK→LineupTemplate)
- `slot_type` (enum: FWD/DEF/G)
- `slot_label` (str; e.g., `FWD1-LW`)
- `order_index` (int)
- `player_id` (FK→Player, nullable)

---

## 4) Active Team & Session Model
- On launch: **Team Selector** (choose or create).
- Session holds `active_team_id` until user switches.
- Archived teams = stored in DB, not active.

---

## 5) UI Flows

### 5.1 Team Selector → Dashboard
- Select team or create new.
- Dashboard (MVP = Quick Actions only):
  - Add Player
  - Manage Roster
  - Create Lineup
  - Load Lineup

### 5.2 Roster Management
- **List View Columns:**  
  `Name | Position | Jersey # | Hand | Birthdate | Email | Phone | Status | Actions`
- Filters: position, hand, birth year.
- Sorts: year, jersey, position, name.
- Bulk actions: Delete, Export CSV, Change Status.

**Add/Edit Player**
- Required: `name`, `position`
- Constraints: position ∈ {F,D,G}, jersey 1–99, hand ∈ {L,R}, birthdate YYYY-MM-DD
- Modal forms.

**CSV Import/Export**
- Headers: `name,position,jersey,hand,birthdate,email,phone,status`
- Missing optional → blank
- Invalid → clear + flag
- Duplicates → allow + flag
- Import report with counts and downloadable issues CSV.

### 5.3 Lineup Builder
- Create template: name, notes → system seeds slots.
- **Drag-and-drop board:**
  - Left: Available players (grey/flag if Affiliate/Injured/Inactive).
  - Right: 4 FWD lines, 3 DEF pairs, 2 Goalies.
  - Duplicate players allowed → warning.
- **Save** button persists.
- **Export PDF** → on-ice slots only.

**Player Cards**
- Show: Name, Jersey, Position, Hand, Status tag.

---

## 6) Validation & Error Handling

### Input Validation
- Position ∈ {F,D,G}, Hand ∈ {L,R}
- Jersey 1–99 if provided
- Birthdate = ISO date
- Status in enum
- Team uniqueness (name+season)

### Roster Import
- Invalid fields cleared + flagged
- Issues reported in JSON + CSV

### Lineup
- Slots validated
- Player must belong to team
- Warnings for duplicates and non-Active players

### Responses
- 400 bad data
- 404 not found
- 409 conflict
- 422 validation
- 500 server error

---

## 7) API Endpoints (initial)

**Teams**
- `GET /api/teams`
- `POST /api/teams`
- `GET /api/teams/{id}`

**Players**
- `GET /api/teams/{team_id}/players`
- `POST /api/teams/{team_id}/players`
- `PUT /api/players/{id}`
- `DELETE /api/players/{id}`
- `POST /api/teams/{team_id}/players/import_csv`
- `GET /api/teams/{team_id}/players/export_csv`

**Lineups**
- `GET /api/teams/{team_id}/lineups`
- `POST /api/teams/{team_id}/lineups`
- `GET /api/lineups/{template_id}`
- `PUT /api/lineups/{template_id}/slots`
- `POST /api/lineups/{template_id}/save`
- `GET /api/lineups/{template_id}/export_pdf`

**Backup**
- `GET /api/backup`
- `POST /api/restore`

---

## 8) PDF Export Layout
- Header: Team name, season, template name, date.
- Sections:
  - Forwards (FWD1–4, LW/C/RW)
  - Defense (DEF1–3, L/R)
  - Goalies (Starter, Backup)
- Styling: clean, light borders, team name bold, optional logo.

---

## 9) Data Handling & Backup
- SQLite file in `~/.coach_app/data.db`.
- Backup: copy DB with timestamp.
- Restore: replace DB, restart app.

---

## 10) Security
- Single-user, no login.
- Local only, no CORS.

---

## 11) Non-Functional
- Performance: <150ms ops
- Reliability: transactions, rollback
- Maintainability: services + type hints
- Portability: Windows/macOS

---

## 12) Testing Plan

### Unit
- Validators, CSV service, Lineup service

### Integration
- Team → Player → CSV → Lineup

### E2E
- Create team, add players, build lineup, save, export PDF.

### Acceptance
1. Team unique
2. Roster CRUD + bulk
3. CSV import/export with flags
4. Lineup seeding & DnD
5. Warnings (duplicate/non-Active)
6. Save button sets `date_saved`
7. PDF export correct layout
8. Backup/restore functional

---

## 13) Implementation Notes
- Slots fixed set
- Warnings as payload metadata
- Sorting: Position → Jersey → Name
- Modal forms for players
- Status chips in roster & lineup cards

---

## 14) Milestones
1. Scaffolding & DB
2. Roster UI + CSV
3. Lineup Builder
4. PDF + Backup
5. Polish

---

## 15) Developer Setup
- Python 3.12+
- System deps for WeasyPrint (Cairo, Pango, GDK-PixBuf)
- Install:  
  `pip install fastapi uvicorn[standard] sqlmodel jinja2 python-multipart weasyprint`
- Run:  
  `uvicorn app.main:app --reload`
- Open:  
  `http://localhost:8000`
