# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Constraints

- **Decoupled Architecture**: Frontend (Flask) and Backend (FastAPI) must remain decoupled and run on different ports.
- **Database**: MySQL must run in a dedicated Docker container; the database must be relational and accessible only to the backend.
	- **Auditability**: All significant system actions must be logged in an audit trail.
- **Security**: The application must implement user authentication, roles, and permissions.
- **Documentation**: The backend must provide Swagger/OpenAPI documentation.

## Architecture

The project is a decoupled web application for managing restaurant requisitions, consisting of a FastAPI backend and a Flask frontend.

- **Backend (`/backend`)**:
  - **Framework**: FastAPI.
  - **Database**: MySQL (orchestrated via Docker).
  - **ORM**: SQLAlchemy.
  - **Functionality**: Provides RESTful endpoints for authentication, administration, and requisition management (ordering and shipping).
  - **Key Directories**:
    - `backend/routers/`: Contains the API endpoint definitions (auth, admin, requis/production).
    	- `backend/models/`: Defines SQLAlchemy database models.
    	- `backend/database.py`: Database connection and engine configuration.

- **Frontend (`/frontend`)**:
  - **Framework**: Flask.
  - **Internationalization**: Flask-Babel (supports English and Spanish).
  - **Templates**: Located in `frontend/templates/`, using Jinja2.
  - **Functionality**: Web interface for different user roles: Admin, Restaurant (ordering/receiving), and Production Plant (shipping).

- **Infrastructure**:
  - **Orchestration**: Docker Compose manages the MySQL database, backend, and frontend containers.
  - **Database Initialization**: SQL scripts in `/db` are used to seed the database.

## Development Commands

### Environment Setup
- **Start the full stack**: `docker-compose up --build`
- **Stop the stack**: `docker-compose down`
- **Wipe all data (including database volumes)**: `docker-compose down -v`

### Backend Development
- **Install dependencies**: `pip install -r backend/requirements.txt`
- **Run server**: `uvicorn backend.main:app --reload --port 8000`
- **API Documentation**: Accessible via Swagger UI at `http://localhost:8000/docs`

### Frontend Development
- **Install dependencies**: `pip install -r frontend/requirements.txt`
- **Run server**: `python frontend/app.py` (runs on port 5000)

### Internationalization (i18n)
To update translations after modifying templates or code:
```bash
# 1. Extract strings into messages.pot
pybabel extract -F ../frontend/babel.cfg -k _ -o ../frontend/messages.pot ../frontend/

# 2. Update the existing .po catalog
pybabel update -i ../frontend/messages.pot -d ../frontend/translations

# 3. Apply translations (requires polib)
pip install polib
python ../frontend/translate.py

# 4. Compile to binary .mo
pybabel compile -d ../frontend/translations
```

### Database Management
- **Seed Product Data**: Run the following from the root to populate categories:
  ```bash
  docker compose exec db mysql -u api_user -papipassword requisitions_db < db/abarrotes.sql
  # (Repeat for other categories: PROTEINAS, panaderia, etc.)
  ```
- **Inspect Database**: Use a MySQL client connected to the `db` service on port `3306`.

## Project Structure
- `backend/`: FastAPI application source code.
- `frontend/`: Flask application source code and templates.
- `db/`: SQL initialization scripts.
- `docker-compose.yml`: Docker orchestration configuration.
