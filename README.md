# CMRS — Cash Management & Reconciliation System

Tracks cash loan repayments through their whole life:

**Customer → Collection agent → Branch → Bank deposit → Company account**

At every step the app records who holds the money and how much, and flags any amount that goes missing or doesn't match.

- **Live app:** https://cmrs-ruby.vercel.app
- **API docs (Swagger):** https://cmrs-hrw2.onrender.com/api/docs

| Part | Stack |
|---|---|
| Backend | Django 5 + Django REST Framework, JWT (simplejwt), django-filter, Swagger (drf-spectacular) |
| Database | PostgreSQL on Neon |
| Frontend | React + Vite, Tailwind CSS, shadcn/ui, react-router, axios |
| Hosting | Render (API), Vercel (frontend), Neon (DB) |

## Transaction lifecycle

```
Installment due (Expected)
   │ agent records payment                 → Collection: COLLECTED       (cash with agent)
   │ agent submits all cash in hand        → SUBMITTED                   (awaiting branch count)
   │ manager counts & approves             → BRANCH_RECEIVED             (short/excess → Discrepancy)
   │    └ or rejects                       → back to COLLECTED
   │ manager deposits reconciled cash      → DEPOSITED                   (amount must match exactly)
   │ finance confirms bank credit          → SETTLED                     (different amount → Discrepancy)
   │    └ or marks the deposit failed      → back to BRANCH_RECEIVED
```

## Roles

| Role | Scope | Does |
|---|---|---|
| Admin | Everything | Adds agents, customers and loans in the app; branches and other users in Django admin |
| Finance | All branches | Settles or fails bank deposits, resolves discrepancies |
| Branch Manager | Own branch | Counts and approves/rejects agent cash, records bank deposits, resolves discrepancies |
| Collection Agent | Assigned customers | Records repayments, submits cash in hand to the branch |

## Business cases

| Case | How it's handled |
|---|---|
| Partial repayment | Applied to the oldest unpaid EMI, which becomes `PARTIAL` |
| Paying more than one EMI | The extra is applied to the next EMIs in order |
| Over-collection | More than the total outstanding is rejected; the error states the excess |
| Duplicate collection | Each payment form sends an `idempotency_key`; a retry returns the original receipt |
| Cash discrepancy | Manager enters the cash counted; any difference becomes a `SHORT`/`EXCESS` discrepancy with mandatory remarks |
| Rejected cash submission | Reason required; the cash goes back to the agent, who resubmits; history is kept |
| Bank deposit mismatch | Deposit amount must equal the branch's reconciled total, otherwise rejected. A bank credit that differs creates a `BANK_MISMATCH` discrepancy |
| Duplicate bank reference | `UNIQUE(bank_name, reference)` after trimming and uppercasing |
| Unauthorized modification | No edit/delete endpoints for money records (`405`), read-only Django admin, reviewed records locked, role-scoped queries (`404` outside scope), every action in an append-only audit log |
| Failed settlement | Finance marks it failed; the cash returns to the branch for a new deposit |
| Delayed settlement | A pending deposit older than `SETTLEMENT_DELAY_DAYS` (default 2) shows `DELAYED` |

## Assumptions

- **Interest is flat:** total interest = principal × annual rate × tenure (years). EMI = (principal + interest) ÷ months. The last EMI absorbs paisa rounding, so the schedule adds up exactly.
- Loans are repaid **monthly**. The first EMI is due one month after disbursement. The interest rate is entered as an **annual %**.
- A loan can't be edited after creation; its schedule is fixed. It closes automatically when fully paid.
- A customer belongs to one branch and has one assigned agent. The branch is taken from the agent.
- An agent hands over **all** the cash they hold in one submission, and a manager deposits **all** reconciled branch cash in one deposit. This mirrors end-of-day handovers and keeps the UI free of selection lists.
- A cash discrepancy doesn't block approval. It's recorded, and only the cash actually received moves on to the bank. Discrepancies stay open until someone resolves them with a note.
- Corrections are never made by editing a money record. They're new, audited actions (reject, fail, resolve).
- Branches and users are managed by the admin in Django admin. Everything else is done in the app.
- Amounts are in INR, stored as `NUMERIC(14,2)` and handled as `Decimal`. The API sends money as strings, and the frontend only displays them.
- Times are in IST (`Asia/Kolkata`). The payment gateway (UPI) was out of scope.

## Architecture

```
React (Vercel) ──JWT──▶ Django REST API (Render) ──▶ PostgreSQL (Neon)
```

```
backend/
  config/      settings, urls
  accounts/    User (role, branch), Branch, JWT login, role permissions, seed_demo
  audit/       append-only AuditLog + log_action()
  lending/     Customer, Loan, Installment; flat-interest schedule (services.py)
  cash/        Collection, CashSubmission, BankDeposit, Discrepancy;
               all money movements in services.py; dashboard.py
frontend/src/
  lib/         api client (token refresh), auth context, nav per role, formatting
  pages/       one file per screen, built from shadcn/ui components
```

- **Views stay thin.** Every money movement is a function in `cash/services.py` that runs in one transaction, locks the rows it changes (`select_for_update`), validates the state change and writes an audit entry.
- **Totals are computed by the database** (`SUM` aggregates), never in Python loops or in the browser.
- **Role scoping** is applied in each viewset's `get_queryset`, so records outside a user's scope return 404.

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
| `SETTLEMENT_DELAY_DAYS` | no | Days after which an unsettled bank deposit is flagged delayed (default `2`) |
| `LOGIN_RATE` | no | Login attempts allowed per client (default `10/min`) |
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

The seed also walks cash through every stage, so each case is visible right away:

- **Bengaluru:** a submission approved ₹100 short (open `SHORT` discrepancy), deposited to HDFC and settled. A rejected submission. `agent_blr` holds ₹2,500 ready to submit.
- **Mumbai:** an SBI deposit pending for 5 days (`DELAYED`). An ICICI deposit settled ₹62.50 short (`BANK_MISMATCH`). A submission waiting for `manager_mum` to review.

## API

All endpoints are under `/api/v1/` and need `Authorization: Bearer <access token>`, except login and refresh. Full interactive docs are at `/api/docs/`.

| Method | Path | Description |
|---|---|---|
| POST | `/auth/login/` | `{username, password}` → `{access, refresh}` (rate limited) |
| POST | `/auth/refresh/` | `{refresh}` → `{access}` |
| GET | `/auth/me/` | Current user with role and branch |
| GET | `/branches/` | All branches |
| GET, POST | `/agents/` | Active collection agents (admin, finance; managers see their branch) / add an agent: `{username, first_name, last_name, password, branch}` (admin) |
| GET | `/dashboard/` | Totals for `date_from`, `date_to`, `branch`, `agent`: expected, collected, with agents, received at branch, deposited, settled, outstanding, open discrepancies, pending deposits, and a by-agent breakdown |
| GET, POST | `/customers/` | List (scoped by role) / create (admin) |
| GET, PATCH | `/customers/{id}/` | Detail / update (admin) |
| GET, POST | `/loans/` | List with `amount_paid` and `outstanding` / create with auto-generated schedule (admin) |
| GET | `/loans/{id}/` | Loan detail with its installments |
| GET, POST | `/collections/` | List with `total` and `count` (filters: `date_from`, `date_to`, `status`, `loan`, `agent`) / record a cash repayment (agent) |
| GET | `/collections/{id}/` | Collection with its receipt number |
| GET, POST | `/submissions/` | List: `{results, by_agent, total}`, where each submission includes its receipts and the totals are expected/received/difference per agent and overall (filters: `status`, `agent`, `branch`) / submit all cash in hand to the branch (agent) |
| POST | `/submissions/{id}/approve/` | `{received_amount, remarks}`. A difference creates a discrepancy, and remarks are then required (branch manager) |
| POST | `/submissions/{id}/reject/` | `{remarks}`. The cash goes back to the agent, who can resubmit (branch manager) |
| GET, POST | `/deposits/` | List (filters: `status`, `branch`) / deposit all reconciled branch cash: `{bank_name, reference, amount, deposit_date}` (branch manager) |
| GET | `/deposits/eligible/` | Reconciled cash ready to deposit: `{total, count, refs}` (branch manager) |
| POST | `/deposits/{id}/settle/` | `{settled_amount, settled_on, remarks}`. A difference creates a bank-mismatch discrepancy (finance) |
| POST | `/deposits/{id}/fail/` | `{remarks}`. The cash goes back to the branch for a new deposit (finance) |
| GET | `/discrepancies/` | List (filters: `status`, `type`, `branch`) |
| POST | `/discrepancies/{id}/resolve/` | `{resolution_note}` (branch manager, finance, admin) |

**Filtering:** the dashboard filters by date, branch and agent. The collections, submissions, deposits and discrepancies lists filter by status.

**Visibility:** agents see only their own customers, loans and cash. Branch managers see their branch. Admin and finance see everything. Records outside a user's scope return 404.

**Errors:** validation errors return `400` with `{field: [message]}`, auth failures `401`, wrong role `403`, out of scope `404`, edits to money records `405`, too many logins `429`.

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
| `cash_bankdeposit` | Bank deposits: bank, reference, amount, date, status `PENDING / SETTLED / FAILED`, `settled_amount`, `settled_on`. `UNIQUE(bank_name, reference)` |
| `cash_bankdeposit_submissions` | Which approved submissions each deposit covers |
| `cash_discrepancy` | `SHORT / EXCESS / BANK_MISMATCH`: expected, actual, `difference = expected − actual`, note, `OPEN / RESOLVED` |

```
Branch 1─* User(agent/manager)      Branch 1─* Customer *─1 User(agent)
Customer 1─* Loan 1─* Installment   Loan 1─* Collection *─1 User(agent)
CashSubmission *─* Collection       BankDeposit *─* CashSubmission
Discrepancy *─1 CashSubmission | BankDeposit
```

All money columns are `NUMERIC(14,2)`. Amounts must be positive (`CHECK` constraints).

## Design decisions and trade-offs

- **One status per collection** instead of a double-entry ledger. It's easy to follow and enough for a single currency and a single company account. A ledger would be the next step for multi-account accounting.
- **Derived values are computed, not stored:** receipt, loan and submission numbers come from the id, `OVERDUE` and `DELAYED` from dates. Nothing can drift, and the delayed check needs no background job.
- **Many-to-many links** (submission↔collections, deposit↔submissions) so rejected and failed attempts keep their history while the cash moves on.
- **Hand over everything at once** (agent → branch, branch → bank). This removes selection UIs and partial-handover edge cases, at the cost of flexibility.
- **No Redis, Celery or Docker.** Nothing runs in the background, and Render and Neon cover hosting. The login rate limit uses the in-process cache, which is fine for a single worker.

## What I'd improve with more time

- Reversal entries for mistaken collections (currently a collection can never change).
- Pagination and CSV export on lists; charts for collection trends.
- A UPI payment gateway (sandbox) whose payments skip the branch steps and are matched at settlement.
- A double-entry ledger, cash limits per agent, and end-of-day alerts for cash not submitted.
- HttpOnly-cookie auth instead of `localStorage` tokens, and Redis for shared rate limits.
