# CMRS — Cash Management & Reconciliation System

Tracks cash repayments from customer → collection agent → branch → bank deposit → company account.

| Part | Stack |
|---|---|
| Backend | Django 5 + Django REST Framework, JWT (simplejwt), Swagger (drf-spectacular) |
| Database | PostgreSQL on Neon |
| Frontend | React + Vite, Tailwind CSS, shadcn/ui, react-router, axios |
| Hosting | Render (API), Vercel (frontend), Neon (DB) |

## Roles

| Role | Scope |
|---|---|
| Admin | Everything; manages branches, users, customers, loans |
| Finance | All branches; confirms bank settlements |
| Branch Manager | Own branch; verifies agent cash, creates bank deposits |
| Collection Agent | Assigned customers; records collections, submits cash to branch |

## Local setup

Needs Python 3.12+, Node 20+ and a free [Neon](https://neon.tech) database. No local Postgres required.

### Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # paste your Neon DATABASE_URL and set SECRET_KEY
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
.venv/bin/python manage.py runserver
```

- API: http://localhost:8000/api/v1/
- Swagger docs: http://localhost:8000/api/docs/
- Django admin: http://localhost:8000/admin/ (log in as `admin`)

Run tests: `.venv/bin/python manage.py test`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173.

## Environment variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | yes | Django secret key (long random string) |
| `DATABASE_URL` | yes | Neon connection string (`...?sslmode=require`) |
| `DEBUG` | no | `true` locally, `false` in production (default `false`) |
| `ALLOWED_HOSTS` | no | Comma-separated API hostnames (default `localhost,127.0.0.1`) |
| `CORS_ALLOWED_ORIGINS` | no | Comma-separated frontend URLs (default `http://localhost:5173`) |
| `DEMO_PASSWORD` | no | Password `seed_demo` gives every demo user (default `Demo@12345`) |

### Frontend (`frontend/.env`)

| Variable | Description |
|---|---|
| `VITE_API_URL` | API base URL, e.g. `http://localhost:8000/api/v1` |

## Test credentials

Created by `manage.py seed_demo`. Password for all: `Demo@12345`.

| Username | Role | Branch |
|---|---|---|
| `admin` | Admin | — |
| `finance` | Finance | — |
| `manager_blr` | Branch Manager | BLR01 Bengaluru Central |
| `agent_blr` | Collection Agent | BLR01 Bengaluru Central |
| `manager_mum` | Branch Manager | MUM01 Mumbai Andheri |
| `agent_mum` | Collection Agent | MUM01 Mumbai Andheri |

## API

All endpoints are under `/api/v1/` and need `Authorization: Bearer <access token>` except login and refresh. Full docs at `/api/docs/`.

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login/` | `{username, password}` → `{access, refresh}` |
| POST | `/auth/refresh/` | `{refresh}` → `{access}` |
| GET | `/auth/me/` | Current user with role and branch |

## Database

| Table | Purpose |
|---|---|
| `accounts_branch` | Branches (`code` unique) |
| `accounts_user` | Users with `role` and `branch` (branch required for managers and agents) |
| `audit_auditlog` | Append-only log of who changed what (`before` / `after` JSON) |

## Deployment

**Neon:** create a project and copy the connection string.

**Render (API)** — New Web Service from this repo:
- Root directory: `backend`
- Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_demo`
- Start command: `gunicorn config.wsgi`
- Env vars: `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS=<your-app>.onrender.com`, `CORS_ALLOWED_ORIGINS=https://<your-app>.vercel.app`

**Vercel (frontend)** — import this repo:
- Root directory: `frontend` (Vite preset)
- Env var: `VITE_API_URL=https://<your-app>.onrender.com/api/v1`
