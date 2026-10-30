# SmartAssist — Connecting Needs to Support

A starter MVP for community assistance reporting and NGO coordination. Stack: HTML/CSS/JavaScript, FastAPI, PostgreSQL, rule-based NLP triage, Leaflet, and OpenStreetMap.

## Included
- Citizen report form (no account required), unique case IDs, optional browser geolocation.
- Rule-based support classification (food/shelter/medical/other), summary, and urgent-review keyword flagging.
- Similar-report flagging for human review (token Jaccard similarity).
- PostgreSQL persistence and REST API.
- Dashboard metrics, search/filter, case status, NGO list, map markers.
- Verified NGO matching by category, availability/capacity, and distance when report coordinates exist.
- JWT sign-in and role checks for verification, assignment, and status updates.
- Seed demo NGO records on first startup.

## Requirements
- Python 3.10+
- PostgreSQL 14+ (or another compatible recent PostgreSQL version)

## Run locally

1. Create a PostgreSQL database:

   ```sql
   CREATE DATABASE smartassist;
   ```

2. Open a terminal in this project folder and create a virtual environment:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. Install packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set `DATABASE_URL` and a long random `SECRET_KEY`. Export the variables in your terminal or use a dotenv runner. This project intentionally does not auto-load `.env` unless you install/configure a dotenv loader.

   Windows PowerShell example:

   ```powershell
   $env:DATABASE_URL="postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/smartassist"
   $env:SECRET_KEY="replace-with-a-long-random-secret"
   ```

   macOS/Linux example:

   ```bash
   export DATABASE_URL='postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/smartassist'
   export SECRET_KEY='replace-with-a-long-random-secret'
   ```

5. Start the app from the project folder:

   ```bash
   uvicorn app.main:app --reload
   ```

6. Open http://127.0.0.1:8000. API documentation is at http://127.0.0.1:8000/docs.

## Create an authorized staff account for local testing

Public registration intentionally creates citizen accounts only. To create a field-worker account for the demo, run this from the project folder after installing requirements and setting `DATABASE_URL`:

```bash
python -c "from app.database import Base,engine,SessionLocal; from app.models import User; from app.security import hash_password; Base.metadata.create_all(engine); db=SessionLocal(); db.add(User(name='Demo Field Worker',email='worker@smartassist.local',password_hash=hash_password('ChangeMe123!'),role='field_worker')); db.commit(); db.close(); print('Created local demo account')"
```

Use `worker@smartassist.local` / `ChangeMe123!` to test staff actions, then change or remove this demo account. This account is only for a local demo and must never be deployed with this password. In production, use an admin-controlled invitation process and do not allow users to self-select privileged roles.

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/auth/register` | Citizen registration |
| POST | `/api/auth/login` | Sign in / JWT token |
| POST | `/api/reports` | Create a report |
| GET | `/api/reports` | List reports (supports `status_filter` and `category`) |
| GET | `/api/reports/{case_code}` | View one case |
| GET | `/api/reports/{case_code}/matches` | Eligible NGO recommendations |
| POST | `/api/reports/{case_code}/verify` | Field worker/admin verifies or rejects |
| POST | `/api/reports/{case_code}/assign` | Assign a verified case to an NGO |
| POST | `/api/reports/{case_code}/status` | Update assigned case status |
| GET | `/api/ngos` | List NGO records |
| GET | `/api/dashboard` | Dashboard counts |

## Important limitations before real-world use
- The AI is a transparent keyword-based prototype, not a trained model and not a substitute for human triage. Urgent flags must be reviewed promptly; absence of a flag does not mean a case is safe.
- Duplicate matching is heuristic and may flag unrelated reports or miss genuine duplicates.
- Seed NGOs are fictional demo records. Replace them with verified organizations and confirmed capacity before any public deployment.
- Add audit logs, rate limiting, CSRF/security review where applicable, privacy/retention controls, NGO onboarding, consent notices, and stronger staff/NGO authorization before production.
- Public case listing currently returns report details for a classroom MVP. Before deployment, protect personal/contact data, implement scoped access, and return a public-safe projection.
- For production, add database migrations (Alembic), automated tests, monitoring, backups, and HTTPS.
