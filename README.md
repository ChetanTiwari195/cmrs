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
| `DATABASE_URL` | yes | Neon **direct** connection string (pooling off; the pooler breaks `manage.py test`) |
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

The seed also creates 4 customers with one loan each: 2 per agent.

## API

All endpoints are under `/api/v1/` and need `Authorization: Bearer <access token>` except login and refresh. Full docs at `/api/docs/`.

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login/` | `{username, password}` → `{access, refresh}` |
| POST | `/auth/refresh/` | `{refresh}` → `{access}` |
| GET | `/auth/me/` | Current user with role and branch |
| GET | `/agents/` | Active collection agents (admin only) |
| GET, POST | `/customers/` | List (scoped by role) / create (admin) |
| GET, PATCH | `/customers/{id}/` | Detail / update (admin) |
| GET, POST | `/loans/` | List with `amount_paid` and `outstanding` / create with auto-generated schedule (admin) |
| GET | `/loans/{id}/` | Loan detail with its installments |

| GET, POST | `/collections/` | List with `total` and `count` (filters: `date_from`, `date_to`, `status`, `loan`, `agent`) / record a cash repayment (agent) |
| GET | `/collections/{id}/` | Collection with its receipt number |

| GET, POST | `/submissions/` | List (filters: `status`, `agent`, `branch`) / submit all cash in hand to the branch (agent) |
| POST | `/submissions/{id}/approve/` | `{received_amount, remarks}`. A difference creates a discrepancy, and remarks are then required (branch manager) |
| POST | `/submissions/{id}/reject/` | `{remarks}`. The cash goes back to the agent, who can resubmit (branch manager) |
| GET | `/discrepancies/` | List (filters: `status`, `type`, `branch`) |
| POST | `/discrepancies/{id}/resolve/` | `{resolution_note}` (branch manager, finance, admin) |

**Visibility:** agents see only their assigned customers and their loans, branch managers see their branch, and admin and finance see everything. Out-of-scope records return 404.

## Database

| Table | Purpose |
|---|---|
| `accounts_branch` | Branches (`code` unique) |
| `accounts_user` | Users with `role` and `branch` (branch required for managers and agents) |
| `audit_auditlog` | Append-only log of who changed what (`before` / `after` JSON) |
| `lending_customer` | Customers (`phone` unique), with branch and assigned agent |
| `lending_loan` | Loans: principal, flat annual rate, tenure, `total_interest`, `total_payable`, status. Loan number is `LN` + zero-padded id |
| `lending_installment` | EMI schedule: `seq`, `due_date`, `amount_due`, `amount_paid`, status. `UNIQUE(loan, seq)`, `CHECK 0 <= amount_paid <= amount_due` |

| `cash_collection` | Cash repayments: loan, agent, amount, status (`COLLECTED → SUBMITTED → BRANCH_RECEIVED → DEPOSITED → SETTLED`), `idempotency_key` unique. Receipt number is `RC` + date + id |
| `cash_cashsubmission` | Agent → branch cash handovers: `expected_amount` (sum of collections), `received_amount`, status `PENDING / APPROVED / REJECTED`, remarks, reviewer |
| `cash_cashsubmission_collections` | Which collections are in each submission. Many-to-many, so rejected submissions keep their history |
| `cash_discrepancy` | `SHORT / EXCESS / BANK_MISMATCH`: expected, actual, `difference = expected − actual`, note, `OPEN / RESOLVED` |

All money columns are `NUMERIC(14,2)`.

### Collection rules

- The payment goes to the oldest unpaid EMI first, and anything extra goes to the next EMIs. A loan is closed when it's fully paid.
- **Over-collection:** an amount above the total outstanding is rejected, and the error states the excess.
- **Duplicate collection:** each payment form sends a unique `idempotency_key`, and a retry returns the original receipt (`200`) instead of creating a second payment.
- Only the customer's assigned agent can collect. Collections can never be edited or deleted (`405`).

### Branch reconciliation rules

- The agent submits **all** the cash they hold in one go. The expected amount is calculated on the server.
- The manager enters the cash actually counted. A difference is recorded as a SHORT or EXCESS discrepancy (remarks required), and only the received amount moves on to the bank.
- Rejecting needs a reason. The collections go back to the agent, who can resubmit.
- An approved or rejected submission is locked: it can't be reviewed again or edited (`405`), and every action is audit-logged.

### Loan schedule (flat interest)

- Total interest = principal × annual rate × tenure months / 1200
- EMI = (principal + interest) / tenure, rounded down to the paisa
- The last EMI takes the rounding remainder, so the schedule always adds up exactly to the total payable
- EMIs are monthly. The first one is due one month after disbursement (clamped to month end, e.g. Jan 31 → Feb 28)

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
