# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

The project is a decoupled web application for managing restaurant requisitions, consisting of a FastAPI backend and a Flask frontend.

- **Backend (`/backend`)**:
  - **Framework**: FastAPI.
  - **Database**: MySQL (orchestrated via Docker).
  - **ORM**: SQLAlchemy.
  - **Functionality**: Provides RESTful endpoints for authentication, administration, and requisition management (ordering and shipping).
  - **Key Directories**:
    - `backend/routers/`: Contains the API endpoint definitions (auth, admin, requisitions, production).
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
- Start the full stack: `docker-compose up --build`

### Backend Development
- Install dependencies: `pip install -r backend/requirements.txt`
- Run server: `uvicorn backend.main:app --reload --port 8000`
- API Documentation: Accessible via Swagger UI at `http://localhost:8000/docs`

### Frontend Development
- Install dependencies: `pip install -r frontend/requirements.txt`
- Run server: `python frontend/app.py` (runs on port 5000)

### Database
- The database is initialized using scripts in `/db`.
- To inspect the database, use a MySQL client connected to the `db` service on port `3306`.

## Project Structure
- `backend/`: FastAPI application source code.
- `frontend/`: Flask application source code and templates.
- `db/`: SQL initialization scripts.
- `docker-compose.yml`: Docker orchestration configuration.
