# Elite Minor Hockey Coach App — MVP

Local FastAPI app to manage a youth hockey team roster and lineups.

## Requirements
- Python 3.12+
- uv (installed): https://astral.sh/uv

## Setup
```bash
uv sync
```

## Run (dev)
```bash
uv run uvicorn app.main:app --reload
```

## Test
```bash
uv run pytest -q
```

## Lint
```bash
uv run flake8 .
```

## Type Check
```bash
uv run mypy
```
