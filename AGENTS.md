# AGENTS.md

## Critical Gotchas

- **Frontend URL is `localhost:5001`**, not 5000. Docker-compose maps host port 5001 to container port 5000.
- **Database is wiped on `docker compose down -v`** (removes the `db_data` volume). Data is not persistent across down/up cycles.
- **`docker compose`** (space, no hyphen) is the correct command for modern Docker. The hyphenated form is deprecated.
- **No test, lint, or typecheck infrastructure exists.** Do not run these commands — they will fail.

## Architecture

- **Backend entrypoint**: `backend/main.py` → `app = FastAPI(...)`. Routers are imported and included at lines 24-27. Tables are created via `Base.metadata.create_all(bind=engine)` at line 7 — no Alembic migrations.
- **Frontend entrypoint**: `frontend/app.py` runs Flask directly (`app.run(host="0.0.0.0", port=5000)`). Babel locale is resolved from session, then falls back to backend settings.
- **Frontend-to-backend通信**: `API_URL` env var inside Docker is `http://backend:8000` (internal network). `PUBLIC_API_URL` is `http://localhost:8000` for browser-side JS.
- **CORS**: Backend allows `localhost:5000` and `localhost:5001` explicitly (see `backend/main.py:14-17`).

## Non-Obvious Commands

```bash
# Start stack (builds images if needed)
docker compose up --build

# Tear down and wipe database
docker compose down -v

# Seed product data (run on a running db container)
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/abarrotes.sql
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/PROTEINAS.SQL
# ... other category scripts (product_groups must exist first)

# Update i18n translations (single command via frontend container)
docker compose exec frontend sh -c "pybabel extract -F babel.cfg -k _ -o messages.pot . && pybabel update -i messages.pot -d translations && pip install -q polib && python translate.py && pybabel compile -d translations"

# Backend dev (runs on port 8000)
cd backend && uvicorn backend.main:app --reload --port 8000

# Frontend dev (runs on port 5000)
cd frontend && python app.py
```

## Seed Script Ordering

Product groups must exist before product data scripts run. The `init.sql` schema creates the groups table but typically only seeds the admin user. Run product group seeders first, then product seeders, in this order:

```
abarrotes.sql → PROTEINAS.SQL → panaderia.sql → pasteleria.sql → lacteos.sql → pulpas.sql → preparados.sql → aseo-empaques.sql
```

Note: `PROTEINAS.SQL` uses uppercase — this matters on case-sensitive filesystems.

## Key Files

- `docker-compose.yml` — canonical port mappings and env vars (truth over CLAUDE.md)
- `db/init.sql` — schema + admin user seed
- `frontend/translate.py` — custom i18n post-processing (required after pybabel update)
- `backend/database.py` — SQLAlchemy engine/session setup
- `backend/dependencies.py` — JWT auth helpers and audit logger

## Secrets

Default credentials (`admin`/`admin123`) and `SECRET_KEY=supersecretkey_change_in_production` are hardcoded in `docker-compose.yml`. Change before any non-local deployment.