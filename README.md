# piigacourse

A single-user personal **course tracker**. Sign in is protected by **TOTP MFA**
(authenticator app), and the UI uses a calm **stone theme** with both a **list view**
and a **calendar view** of your courses.

Stack: **React + Vite** frontend, **FastAPI** backend, **PostgreSQL** database.
Everything runs **locally** — no cloud/serverless deployment required.

---

## Prerequisites

- Docker Desktop (for PostgreSQL)
- Python 3.11+
- Node.js 18+

---

## 1. Start PostgreSQL

From the project root:

```powershell
docker compose up -d
```

This launches a `postgres:16` container (`db`) on `localhost:5432` with database
`piigacourse` (user `piiga` / password `piiga`) and a named volume for persistence.
Check it is healthy:

```powershell
docker compose ps
```

---

## 2. Backend (FastAPI)

From the `backend/` directory (PowerShell):

```powershell
# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment: copy the template and edit values
Copy-Item ..\.env.example .env
#   - set SECRET_KEY  (generate:  openssl rand -hex 32)
#   - set BOOTSTRAP_EMAIL / BOOTSTRAP_PASSWORD for your single user

# Apply database migrations
alembic upgrade head

# Create the single bootstrap user (reads BOOTSTRAP_EMAIL / BOOTSTRAP_PASSWORD)
python -m app.bootstrap

# Run the API (http://localhost:8000, docs at /api/docs)
uvicorn app.main:app --reload --port 8000
```

> On first login you will be prompted to enroll TOTP MFA — scan the QR code with
> your authenticator app, then enter the 6-digit code to complete sign in.

---

## 3. Frontend (React + Vite)

From the `frontend/` directory:

```powershell
npm install
npm run dev
```

Open the app at **http://localhost:5173**. API requests to `/api` are proxied to
the backend on port 8000.

---

## Environment variables

All configuration lives in [`.env.example`](./.env.example). Copy it to
`backend/.env` (and the `VITE_*` value to `frontend/.env` if your setup needs it),
then fill in real values. Never commit a real `.env` — only `.env.example` is tracked.

---

## Stopping / resetting

```powershell
docker compose down            # stop Postgres (keeps data)
docker compose down -v         # stop and DELETE the data volume (fresh DB)
```
