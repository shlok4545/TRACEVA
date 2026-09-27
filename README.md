# TRACEVA

TRACEVA is a healthcare waste operations platform prototype for SIH 2026. This repository now includes the Phase 2 implementation: authenticated multi-role access, JWT security, protected routes, facility-aware authorization, and seeded demo identities for local development.

## Phase 2 scope

Implemented in this repository:

- real authentication with password hashing and JWT access tokens
- role-based access control for ADMIN, WARD_STAFF, COLLECTOR, TREATMENT_FACILITY, and REGULATOR
- facility and ward organization with protected facility-level access checks
- protected frontend routes and role-aware navigation
- persistent user records and deterministic seed data
- login/logout flow and user session handling

Intentionally postponed:

- Waste Passport workflows
- QR generation or scanning
- AI or risk scoring
- pickup engine
- treatment verification
- GPS or RFID
- advanced analytics

## Authentication architecture

- Backend: FastAPI + SQLAlchemy + JWT
- Password storage: hashed via passlib + bcrypt
- Token: access token with expiration defined in backend settings
- Session handling: stored in browser localStorage on the frontend
- Authorization: reusable backend dependencies for current-user and role checks

## Roles and permissions

- ADMIN: full user and facility management
- WARD_STAFF: access to own facility and assigned ward data
- COLLECTOR: access to assigned organizational info and collection tasks
- TREATMENT_FACILITY: access to treatment facility records only
- REGULATOR: read-oriented access without mutation rights

## Demo credentials

These are DEMO credentials only and must not be used in production.

- Admin: admin@traceva.demo / Traceva@2026
- Ward Staff: nurse@traceva.demo / Traceva@2026
- Collector: collector@traceva.demo / Traceva@2026
- Treatment Facility: treatment@traceva.demo / Traceva@2026
- Regulator: regulator@traceva.demo / Traceva@2026

## Seed data and database

The database seeds a deterministic set of facilities and wards on startup. Duplicate seeding is prevented by checking for existing email and facility records before inserts.

## Frontend setup

1. Go to `frontend/`
2. Install dependencies:

```bash
npm install
```

3. Start the frontend:

```bash
npm run dev -- --host 0.0.0.0
```

## Backend setup

1. Go to `backend/`
2. Create and activate a virtual environment:

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Start the API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

5. Or run from the repo root with the correct PYTHONPATH during local debugging:

```powershell
$env:PYTHONPATH = "C:\Users\shlok\OneDrive\Desktop\SIH_Traceva\backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Core APIs

- POST /api/auth/login
- GET /api/auth/me
- POST /api/auth/logout
- GET /api/users
- GET /api/users/{id}
- POST /api/users
- PUT /api/users/{id}
- GET /api/facilities
- GET /api/facilities/{id}
- POST /api/facilities
- PUT /api/facilities/{id}
- GET /api/wards
- GET /api/wards/{id}
- POST /api/wards
- PUT /api/wards/{id}

## Frontend authentication flow

1. User visits /login
2. Email/password submitted to /api/auth/login
3. JWT is stored in browser localStorage
4. Auth context fetches /api/auth/me
5. Protected routes check role and auth state
6. User is redirected to the default route for their role on successful login

## Permission model

- Non-authenticated users are redirected to /login
- Providers enforce role and facility access on the backend
- Facility checks prevent cross-facility access through user tampering
- Regulator routes remain read-oriented; no mutation endpoints are exposed to that role

## Notes

This is a prototype-level implementation intended for SIH demonstration and local testing, not a production security system.
