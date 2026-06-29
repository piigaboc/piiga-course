# PiigaCourse — Backend

FastAPI backend for **piigacourse**, a personal, **single-user** online-course
tracker. Runs against a **local PostgreSQL** instance using an async SQLAlchemy
engine with a standard connection pool.

## Stack

- FastAPI + Pydantic v2 / pydantic-settings
- SQLAlchemy 2.0 (async) + asyncpg
- Alembic (migrations — wired in a later task)
- passlib[bcrypt] + python-jose (auth — later task)

## Quickstart

```bash
cd backend

# 1. Create and activate a virtualenv
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env        # Windows: copy .env.example .env
# then edit .env (set SECRET_KEY, DATABASE_URL, bootstrap creds)

# 4. Run the dev server
uvicorn app.main:app --reload --port 8000
```

Open the interactive API docs at: <http://localhost:8000/api/docs>

Health check: <http://localhost:8000/api/health> -> `{"status": "ok"}`

## Local PostgreSQL

Point `DATABASE_URL` at a local Postgres database, e.g.:

```
DATABASE_URL=postgresql+asyncpg://piiga:piiga@localhost:5432/piigacourse
```

Quick Docker option:

```bash
docker run --name piigacourse-pg -e POSTGRES_USER=piiga \
  -e POSTGRES_PASSWORD=piiga -e POSTGRES_DB=piigacourse \
  -p 5432:5432 -d postgres:16
```

## Configuration

All settings load from environment variables or `.env` (see `.env.example`):

| Var                      | Default                                                      | Purpose                                  |
|--------------------------|-------------------------------------------------------------|------------------------------------------|
| `DATABASE_URL`           | `postgresql+asyncpg://piiga:piiga@localhost:5432/piigacourse` | Async SQLAlchemy DSN                     |
| `SECRET_KEY`             | `change-me-in-production`                                    | JWT signing secret                       |
| `ACCESS_TOKEN_EXPIRE_MIN`| `60`                                                        | Access-token lifetime (minutes)          |
| `MFA_PENDING_EXPIRE_MIN` | `5`                                                         | MFA challenge lifetime (reserved)        |
| `CORS_ORIGINS`           | `http://localhost:5173`                                     | Comma-separated allowed origins          |
| `BOOTSTRAP_EMAIL`        | `me@example.com`                                            | Seed account email                       |
| `BOOTSTRAP_PASSWORD`     | `change-me`                                                 | Seed account password                    |

## Layout

```
backend/
├── requirements.txt
├── .env.example
├── README.md
└── app/
    ├── __init__.py
    ├── config.py      # pydantic-settings Settings + cached get_settings()
    ├── db.py          # async engine, session factory, Base, get_db dependency
    └── main.py        # create_app() factory, CORS, /api router, app = create_app()
```

> Models, auth (JWT + MFA), and routers are added in subsequent tasks.
