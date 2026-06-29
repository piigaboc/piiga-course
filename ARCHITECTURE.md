# PiigaCourse — Architecture Document

A personal online-course **tracker**: a web app to catalog courses you're taking,
organize them into lessons, log progress and study time, and visualize how far you've
come. Each user has their own private account (JWT login) and their own courses.

> Status: design doc. Written **before** implementation. Code follows this document.

---

## 1. Goals & Scope

### What it does
- Track **courses** (title, provider/platform, URL, category, status, target date).
- Break courses into **lessons / modules** with a completion checkbox.
- Log **study sessions** (date, minutes spent, notes) against a course.
- Show **progress** (% lessons complete) and **dashboard stats** (total hours, active courses, streak).

### Non-goals (v1)
- No video hosting or content delivery — this tracks *external* courses (Udemy, Coursera, YouTube, etc.).
- No multi-tenant org features, no payments.
- Auth is minimal (single user / optional simple login). See §7.

### Design theme
Minimal. Palette: **grey / green / white**. Clean typography, generous whitespace,
green as the single accent (progress bars, primary buttons, active states).

```
--color-bg:        #FFFFFF   /* white surface           */
--color-surface:   #F7F8F7   /* off-white panels        */
--color-border:    #E3E6E3   /* light grey lines        */
--color-text:      #2E332E   /* near-black grey text    */
--color-muted:     #8A908A   /* secondary grey text     */
--color-accent:    #2F9E5A   /* primary green           */
--color-accent-fg: #FFFFFF   /* text on green           */
--color-accent-sub:#E6F4EC   /* green tint backgrounds  */
```

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                          Vercel                              │
│                                                              │
│   ┌──────────────────────┐      ┌────────────────────────┐  │
│   │  React + Vite (SPA)   │ ───▶ │  FastAPI (Serverless)  │  │
│   │  static build         │ HTTP │  /api/*  python funcs  │  │
│   │  served from CDN      │ JSON │                        │  │
│   └──────────────────────┘      └───────────┬────────────┘  │
│                                              │               │
└──────────────────────────────────────────────┼──────────────┘
                                                │ asyncpg / SQLAlchemy
                                                ▼
                                   ┌────────────────────────┐
                                   │  Vercel Postgres        │
                                   │  (managed, Neon-backed) │
                                   └────────────────────────┘
```

- **Frontend**: React 18 + Vite, built to static assets, served by Vercel's CDN.
- **Backend**: FastAPI running as a **Vercel Python Serverless Function** under `/api`.
- **Database**: **Vercel Postgres** (managed, Neon-backed). Provisioned from the Vercel
  dashboard; its env vars are injected into the deployment automatically. See §5 for the
  pooled-vs-direct connection caveat.

---

## 3. Repository Layout (monorepo)

```
piigacourse/
├── ARCHITECTURE.md            ← this file
├── README.md
├── vercel.json                ← routing: /api → python, everything else → SPA
│
├── frontend/                  ← React + Vite
│   ├── index.html
│   ├── vite.config.ts
│   ├── package.json
│   ├── .env.example           ← VITE_API_BASE_URL
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── theme/             ← CSS variables, global styles (grey/green/white)
│       ├── lib/
│       │   ├── api.ts         ← fetch wrapper, base URL
│       │   └── queryClient.ts ← TanStack Query setup
│       ├── components/        ← Button, Card, ProgressBar, StatTile, Modal…
│       ├── features/
│       │   ├── auth/          ← login/register forms, AuthContext, useAuth, token storage
│       │   ├── courses/       ← list, detail, form, hooks
│       │   ├── lessons/
│       │   └── sessions/      ← study-time logging
│       └── pages/
│           ├── Login.tsx
│           ├── Register.tsx
│           ├── Dashboard.tsx
│           ├── Courses.tsx
│           └── CourseDetail.tsx
│
├── api/                       ← Vercel serverless entrypoint
│   └── index.py               ← exposes FastAPI `app` (ASGI) to Vercel
│
└── backend/                   ← FastAPI application package
    ├── requirements.txt
    ├── app/
    │   ├── main.py            ← create_app(), CORS, router registration
    │   ├── config.py          ← pydantic-settings (DATABASE_URL, CORS origins)
    │   ├── db.py              ← async engine + session dependency
    │   ├── models.py          ← SQLAlchemy ORM models
    │   ├── schemas.py         ← Pydantic request/response models
    │   ├── routers/
    │   │   ├── auth.py        ← register / login / me
    │   │   ├── courses.py
    │   │   ├── lessons.py
    │   │   ├── sessions.py
    │   │   └── stats.py
    │   ├── security.py        ← password hashing, JWT encode/decode, get_current_user
    │   └── crud.py            ← DB query helpers (all user-scoped)
    ├── alembic/               ← migrations
    └── tests/
```

Why monorepo: one deploy, one repo, shared `vercel.json` routing. Frontend and backend
version together.

---

## 4. Data Model

```
User ───< Course ───< Lesson
            │
            └──────< StudySession
```

Every `courses` row belongs to a `users` row. Lessons and sessions inherit ownership
through their parent course. All list/detail queries are **scoped to the current user**
(see §7) — a user can never read or mutate another user's data.

### `users`
| column          | type        | notes                                      |
|-----------------|-------------|--------------------------------------------|
| id              | uuid PK     | `gen_random_uuid()`                        |
| email           | text UNIQUE | login identifier, required                 |
| password_hash   | text        | bcrypt/argon2 hash (never the raw password)|
| display_name    | text        | nullable                                   |
| created_at      | timestamptz | default now                                |

### `courses`
| column        | type        | notes                                            |
|---------------|-------------|--------------------------------------------------|
| id            | uuid PK     | `gen_random_uuid()`                              |
| user_id       | uuid FK     | → users.id, on delete cascade (owner)            |
| title         | text        | required                                         |
| provider      | text        | e.g. "Udemy", "YouTube" (nullable)               |
| url           | text        | link to the course (nullable)                    |
| category      | text        | freeform tag, e.g. "Backend" (nullable)          |
| status        | text enum   | `planned` \| `in_progress` \| `completed` \| `paused` |
| target_date   | date        | optional goal date                               |
| created_at    | timestamptz | default now                                      |
| updated_at    | timestamptz | default now, on update                           |

### `lessons`
| column      | type        | notes                                  |
|-------------|-------------|----------------------------------------|
| id          | uuid PK     |                                        |
| course_id   | uuid FK     | → courses.id, on delete cascade        |
| title       | text        | required                               |
| position    | int         | ordering within course                 |
| is_complete | bool        | default false                          |
| completed_at| timestamptz | nullable                               |

### `study_sessions`
| column     | type        | notes                              |
|------------|-------------|------------------------------------|
| id         | uuid PK     |                                    |
| course_id  | uuid FK     | → courses.id, on delete cascade    |
| date       | date        | when studied                       |
| minutes    | int         | duration                           |
| note       | text        | nullable                           |
| created_at | timestamptz | default now                        |

**Derived (not stored):**
- Course progress % = `complete lessons / total lessons`.
- Total hours = `sum(study_sessions.minutes) / 60`.
- Streak = consecutive days with ≥1 session.

Migrations managed by **Alembic** (autogenerate from models).

---

## 5. Database Connection on Serverless (important)

Serverless functions are short-lived and may spin up many concurrent instances. A normal
SQLAlchemy connection pool doesn't fit. Strategy:

- Use **Vercel Postgres** (Neon-backed under the hood). It exposes two connection strings:
  - `POSTGRES_URL` — **pooled** (PgBouncer); use this for the serverless API.
  - `POSTGRES_URL_NON_POOLING` — direct connection; use this for **Alembic migrations**.
- Build the SQLAlchemy async DSN from `POSTGRES_URL` (driver `postgresql+asyncpg://…`);
  configure the async engine with **`NullPool`** so PgBouncer owns pooling.
- Open a session per request via a FastAPI dependency; close it at request end.

```python
# backend/app/db.py (sketch)
engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
```

---

## 6. API Design

Base path: `/api`. JSON in/out. FastAPI auto-docs at `/api/docs`.

| Method | Path                          | Purpose                            |
|--------|-------------------------------|------------------------------------|
| GET    | `/api/health`                 | liveness check (public)            |
| POST   | `/api/auth/register`          | create account (public)            |
| POST   | `/api/auth/login`             | get JWT access token (public)      |
| GET    | `/api/auth/me`                | current user profile               |
| GET    | `/api/courses`                | list **my** courses (filter `status`) |
| POST   | `/api/courses`                | create course                      |
| GET    | `/api/courses/{id}`           | course + lessons + progress        |
| PATCH  | `/api/courses/{id}`           | update course                      |
| DELETE | `/api/courses/{id}`           | delete course (cascade)            |
| POST   | `/api/courses/{id}/lessons`   | add lesson                         |
| PATCH  | `/api/lessons/{id}`           | toggle complete / rename / reorder |
| DELETE | `/api/lessons/{id}`           | delete lesson                      |
| POST   | `/api/courses/{id}/sessions`  | log a study session                |
| GET    | `/api/courses/{id}/sessions`  | list sessions for a course         |
| DELETE | `/api/sessions/{id}`          | delete session                     |
| GET    | `/api/stats`                  | dashboard aggregates               |

All routes except `/api/health`, `/api/auth/register`, and `/api/auth/login` require a
valid `Authorization: Bearer <token>` header.

Conventions: snake_case JSON, `2xx` success, `401` missing/invalid token, `422` validation
(FastAPI default), `404` not found / not owned. Pydantic schemas define every response shape
(passwords/hashes are never returned).

---

## 7. Authentication (JWT)

Email + password login with JWT access tokens. Multi-user from day one.

**Flow**
1. `POST /api/auth/register` — email + password → creates `users` row (password hashed
   with **passlib[bcrypt]** or argon2; raw password never stored).
2. `POST /api/auth/login` — verifies credentials → returns a signed **JWT access token**.
3. Client stores the token and sends `Authorization: Bearer <token>` on every API call.
4. A FastAPI dependency `get_current_user` decodes/verifies the JWT (HS256, `SECRET_KEY`
   env var), loads the user, and injects it into handlers.

**Token strategy (v1)**
- Short-lived **access token** (e.g. 30–60 min) signed with `SECRET_KEY`.
- Refresh tokens deferred — on expiry the user logs in again. (A `/api/auth/refresh`
  endpoint + refresh token can be added later without schema changes.)
- Token claims: `sub` = user id, `exp`, `email`.

**Authorization rule (enforced everywhere):** every course/lesson/session query filters by
`courses.user_id == current_user.id`. Accessing another user's resource returns **404**
(not 403) so existence isn't leaked.

Token storage on the frontend: in-memory + `localStorage` for v1 simplicity (documented
trade-off vs. httpOnly cookies; acceptable for a personal tracker, revisit for XSS hardening).

---

## 8. Frontend Architecture

- **Routing**: React Router — public `/login`, `/register`; protected `/` (Dashboard),
  `/courses`, `/courses/:id` behind a `<ProtectedRoute>` that redirects to `/login` when
  there's no valid token.
- **Auth state**: an `AuthContext` holds the current user + token; `useAuth()` exposes
  `login/register/logout`. Token persisted in `localStorage`, rehydrated on app load.
- **Server state**: **TanStack Query** — caching, mutations, optimistic lesson toggles.
- **Local/UI state**: React `useState` + context for theme; no Redux needed at this scale.
- **Data fetching**: thin `api.ts` wrapper over `fetch` using `VITE_API_BASE_URL`
  (defaults to `/api` in production, `http://localhost:8000/api` in dev). It auto-attaches
  the `Authorization: Bearer` header and triggers logout/redirect on a `401`.
- **Forms**: controlled components; light validation. (React Hook Form optional if forms grow.)
- **Styling**: CSS variables (the §1 palette) + CSS Modules or a small utility layer.
  Reusable primitives: `Button`, `Card`, `ProgressBar`, `StatTile`, `Badge`, `Modal`.

### Key screens
- **Dashboard** — stat tiles (active courses, hours this week, streak), list of in-progress
  courses with progress bars.
- **Courses** — filterable grid/list, status badges, "add course" modal.
- **Course Detail** — header with progress, lesson checklist (toggle), study-session log
  with a quick "add session" form.

---

## 9. Local Development

```
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000           # http://localhost:8000/api/docs

# frontend
cd frontend
npm install
npm run dev                                          # http://localhost:5173
```

- Frontend dev server proxies `/api` → `localhost:8000` (Vite `server.proxy`), so the SPA
  and API feel same-origin in dev.
- Local Postgres via Docker, or point `DATABASE_URL` at a Neon dev branch.

### Environment variables
| Var                        | Where    | Example                                        |
|----------------------------|----------|------------------------------------------------|
| `POSTGRES_URL`             | backend  | pooled DSN (injected by Vercel Postgres)       |
| `POSTGRES_URL_NON_POOLING` | backend  | direct DSN — used by Alembic migrations        |
| `SECRET_KEY`               | backend  | JWT signing secret (long random string)        |
| `ACCESS_TOKEN_EXPIRE_MIN`  | backend  | `60`                                           |
| `CORS_ORIGINS`             | backend  | `http://localhost:5173,https://…vercel.app`    |
| `VITE_API_BASE_URL`        | frontend | `/api`                                         |

> `config.py` derives the SQLAlchemy async DSN from `POSTGRES_URL` (rewriting the scheme to
> `postgresql+asyncpg://`). Locally, set these in `backend/.env`.

---

## 10. Deployment (Vercel)

`vercel.json` ties it together:

```json
{
  "builds": [
    { "src": "frontend/package.json", "use": "@vercel/static-build", "config": { "distDir": "dist" } },
    { "src": "api/index.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/(.*)", "dest": "api/index.py" },
    { "src": "/(.*)", "dest": "frontend/dist/$1" }
  ]
}
```

- `api/index.py` imports the FastAPI `app` — Vercel's `@vercel/python` serves ASGI apps.
- Frontend builds to `frontend/dist`, served as static + SPA fallback.
- **Provision Vercel Postgres** from the dashboard — `POSTGRES_URL*` env vars are injected
  automatically. Add `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MIN`, and `CORS_ORIGINS` manually.
- **Migrations** run outside the deploy (Alembic against `POSTGRES_URL_NON_POOLING`) —
  serverless cold starts should not run migrations.

### Deployment caveats
- Cold starts: first request after idle is slower (acceptable for personal use).
- Use the **pooled** `POSTGRES_URL` for the API to survive function concurrency (§5).
- Keep the Python function lightweight (asyncpg + SQLAlchemy + passlib + python-jose;
  avoid heavy deps to keep cold starts fast).

---

## 11. Tech Stack Summary

| Layer     | Choice                                                |
|-----------|-------------------------------------------------------|
| Frontend  | React 18, Vite, TypeScript, React Router, TanStack Query |
| Styling   | CSS variables + CSS Modules (grey/green/white theme)  |
| Backend   | FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), asyncpg |
| Auth      | JWT (python-jose), passlib[bcrypt] password hashing   |
| Migrations| Alembic (via `POSTGRES_URL_NON_POOLING`)              |
| Database  | Vercel Postgres (managed, Neon-backed)                |
| Hosting   | Vercel (static frontend + Python serverless API)      |
| Testing   | pytest (backend), Vitest + RTL (frontend)             |

---

## 12. Build Order (when we start coding)

1. Scaffold repo + `vercel.json` + env examples.
2. Backend: config, db, `users`+`courses`+`lessons`+`sessions` models, Alembic init.
3. Backend: `security.py` (hashing + JWT), `auth` router (register/login/me), `/health`.
4. Backend: user-scoped courses, lessons, sessions, stats endpoints + tests.
5. Frontend: Vite app, theme tokens, API wrapper (Bearer + 401 handling), Query client.
6. Frontend: AuthContext, Login/Register pages, `<ProtectedRoute>`, router shell.
7. Frontend: Courses list + create, Course detail (lessons), Dashboard, sessions.
8. Provision Vercel Postgres, set `SECRET_KEY`/CORS, deploy, run migrations (direct URL).
```
```

---

## Confirmed Decisions

- **Auth**: ✅ Real login with **JWT** (email + password). `users` table + `user_id` FK on
  courses; all queries user-scoped.
- **DB provider**: ✅ **Vercel Postgres** (pooled URL for API, direct URL for migrations).
- **Frontend language**: TypeScript (assumed — flag if you prefer plain JS).

## Still Open (low-risk, decide during build)

- Refresh tokens vs. re-login on expiry (v1 = re-login).
- Token storage: `localStorage` (v1) vs. httpOnly cookie (hardening) — see §7.
- Styling approach: CSS Modules vs. a utility layer — both honor the §1 token palette.
