# La Cesta — Restaurant Requisition Management System

A full-stack, containerized web application that centralizes the requisition and supply workflow between multiple restaurant locations and a central production plant. Built for **La Cesta - Café Local**.

---

## Table of Contents

- [Overview](#overview)
- [Features by Role](#features-by-role)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)
- [Default Credentials](#default-credentials)
- [Project Structure](#project-structure)
- [Internationalization (i18n)](#internationalization-i18n)
- [Seeding Product Data](#seeding-product-data)

---

## Overview

This system manages the end-to-end supply flow from restaurant to production plant:

```
Restaurant → submits requisition → Production Plant → ships order → Restaurant → confirms receipt → Order Closed
```

All steps are tracked with user attribution (who created, submitted, shipped, and received each order), and every action is written to an audit log.

---

## Features by Role

### 🔑 Admin
- Manage **restaurants**, **users**, **product groups**, and **products** (create, enable/disable).
- Configure system-wide settings:
  - **Requisition ETA** (business days from submission to expected delivery).
  - **Default application language** (English or Spanish).
- Reset any user's password.
- View the complete **audit log** of all system actions.
- View the full **requisition history** across all restaurants.

### 🍽️ Restaurant
- **Daily Requisition Builder**: Input current inventory and required quantities for each product, filtered by product group. Products with zero inventory are highlighted in red.
- Create requisitions for **future dates** (ETA-aware scheduling).
- **Save as draft** or **send directly to production**.
- View personal **requisition history** with item-level detail (required qty, shipped qty, received qty).
- **Receive shipments**: Confirm received quantities when orders arrive from the production plant.
- **Change password** at any time.

### 🏭 Production Plant
- View all **pending submitted orders** across all restaurants, filterable by date.
- Enter and submit **shipped quantities** per item.
- View full **shipping history** and restaurant receival history.
- **Change password** at any time.

---

## Architecture

The application follows a three-tier decoupled architecture managed with Docker Compose:

```
┌─────────────────────────────────────────┐
│            Docker Compose               │
│                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────┐ │
│  │ Frontend │  │ Backend  │  │  DB   │ │
│  │  Flask   │→ │ FastAPI  │→ │ MySQL │ │
│  │ :5001    │  │  :8000   │  │ :3306 │ │
│  └──────────┘  └──────────┘  └───────┘ │
└─────────────────────────────────────────┘
```

- **Frontend** (Flask, port `5001`): Server-side rendered templates via Jinja2. Communicates with the backend over the internal Docker network using JWT tokens stored in the user session.
- **Backend** (FastAPI, port `8000`): Stateless REST API. Handles authentication (JWT), all business logic, and database access via SQLAlchemy.
- **Database** (MySQL 8.0, port `3306`): Persisted via a named Docker volume (`db_data`). Initialized automatically from `db/init.sql`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend Framework | Flask |
| Frontend i18n | Flask-Babel (EN / ES) |
| Frontend Templating | Jinja2 |
| Backend Framework | FastAPI |
| Backend ORM | SQLAlchemy |
| Authentication | JWT (`python-jose`) |
| Password Hashing | bcrypt |
| Database | MySQL 8.0 |
| Containerization | Docker + Docker Compose |

---

## Database Schema

| Table | Description |
|---|---|
| `restaurants` | Restaurant locations (name, location, active flag) |
| `users` | System users with role (`Admin`, `Restaurant`, `Production Plant`) |
| `product_groups` | Categories for products (e.g., Proteínas, Panadería) |
| `products` | Individual items with SKU and unit of measure |
| `orders` | One order per restaurant per date; tracks full lifecycle with user attribution |
| `order_items` | Line items per order (inventory, required qty, shipped qty, received qty) |
| `system_settings` | Key-value store for admin-configurable settings (ETA days, default language) |
| `audit_logs` | Immutable log of all create/update actions with user and timestamp |

**Order Lifecycle:**
```
Draft → Submitted → Shipped → Closed
```

---

## API Endpoints

The backend exposes a fully documented Swagger UI at `http://localhost:8000/docs`.

### Auth (`/auth`)
| Method | Path | Description |
|---|---|---|
| POST | `/auth/login` | Authenticate and receive a JWT token |
| POST | `/auth/change-password` | Change the authenticated user's password |

### Admin (`/admin`) — Admin role only
| Method | Path | Description |
|---|---|---|
| GET/POST | `/admin/settings` | Get or update system settings (ETA, language) |
| GET/POST | `/admin/restaurants` | List or create restaurants |
| POST | `/admin/restaurants/{id}/toggle` | Enable/disable a restaurant |
| GET/POST | `/admin/users` | List or create users |
| POST | `/admin/users/{id}/reset-password` | Force-reset a user's password |
| GET/POST | `/admin/product-groups` | List or create product groups |
| GET/POST | `/admin/products` | List or create products |
| POST | `/admin/products/{id}/toggle` | Enable/disable a product |
| GET | `/admin/audit-logs` | Retrieve all audit log entries |
| GET | `/admin/history` | Requisition history for all restaurants |

### Requisitions (`/requisitions`) — Restaurant role
| Method | Path | Description |
|---|---|---|
| GET | `/requisitions/product-groups` | List active product groups |
| GET | `/requisitions/products` | List active products |
| GET | `/requisitions/eta-days` | Get configured ETA (business days) |
| GET | `/requisitions/active` | Get current or future order for a given date |
| POST | `/requisitions/draft` | Save/update a draft order |
| POST | `/requisitions/send` | Submit an order to the production plant |
| GET | `/requisitions/report` | Summary of all past orders for the restaurant |
| GET | `/requisitions/shipped` | Orders in "Shipped" status awaiting receipt |
| POST | `/requisitions/{id}/receive` | Confirm received quantities and close an order |
| GET | `/requisitions/history` | Full order history with item-level detail |

### Production (`/production`) — Production Plant role
| Method | Path | Description |
|---|---|---|
| GET | `/production/requirements` | All submitted orders pending shipment |
| POST | `/production/{id}/ship` | Record shipped quantities and mark order Shipped |
| GET | `/production/history` | Full history of all non-draft orders |

---

## Getting Started

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

### Run the stack

```bash
git clone <repository-url>
cd requisiciones-restaurante
docker compose up --build
```

The services will be available at:
- **Frontend**: http://localhost:5001
- **Backend API / Swagger UI**: http://localhost:8000/docs
- **MySQL**: `localhost:3306` (user: `api_user`, password: `apipassword`)

### Stop the stack
```bash
docker compose down
```

> [!IMPORTANT]
> To wipe all data (including the database), use `docker compose down -v`. This removes the `db_data` volume.

---

## Default Credentials

After the first run, a single admin account is created automatically:

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Admin |

> [!CAUTION]
> **Change the admin password immediately** after your first login. Also update the `SECRET_KEY` values in `docker-compose.yml` before deploying to any non-local environment.

---

## Project Structure

```
requisiciones-restaurante/
├── backend/                    # FastAPI REST API
│   ├── main.py                 # App entry point, CORS config
│   ├── database.py             # SQLAlchemy engine & session
│   ├── dependencies.py         # JWT auth helpers, audit logger
│   ├── models/
│   │   └── models.py           # SQLAlchemy ORM models
│   ├── routers/
│   │   ├── auth.py             # Login, change-password
│   │   ├── admin.py            # Admin CRUD + history
│   │   ├── requisitions.py     # Restaurant ordering + receiving
│   │   └── production.py       # Production shipping + history
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                   # Flask web application
│   ├── app.py                  # Flask routes & session management
│   ├── babel.cfg               # Babel extraction config
│   ├── translate.py            # Script to apply ES translations
│   ├── messages.pot            # Extracted translatable strings
│   ├── translations/
│   │   └── es/LC_MESSAGES/     # Spanish .po and compiled .mo files
│   ├── templates/              # Jinja2 HTML templates
│   │   ├── base.html           # Navbar, modals, global scripts
│   │   ├── login.html
│   │   ├── welcome.html
│   │   ├── admin_dashboard.html
│   │   ├── restaurant_order.html
│   │   ├── restaurant_receiving.html
│   │   ├── production_shipping.html
│   │   └── history.html
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/app.js
│   ├── requirements.txt
│   └── Dockerfile
│
├── db/
│   ├── init.sql                # Schema creation + admin seed
│   ├── abarrotes.sql           # Grocery product data
│   ├── PROTEINAS.SQL           # Protein product data
│   ├── panaderia.sql           # Bakery product data
│   ├── pasteleria.sql          # Pastry product data
│   ├── lacteos.sql             # Dairy product data
│   ├── pulpas.sql              # Juice/pulp product data
│   ├── preparados.sql          # Prepared foods product data
│   └── aseo-empaques.sql       # Cleaning & packaging supplies
│
└── docker-compose.yml
```

---

## Internationalization (i18n)

The application supports **English** and **Spanish**, selectable per user session via the `EN | ES` toggle in the navbar. The admin can also set the system-wide default language in **System Settings**.

### Updating translations after template changes

Run the following inside the `frontend` container:

```bash
# 1. Extract all marked strings into messages.pot
pybabel extract -F babel.cfg -k _ -o messages.pot .

# 2. Update the existing .po catalog (preserves existing translations)
pybabel update -i messages.pot -d translations

# 3. Apply translations via script
pip install polib
python translate.py

# 4. Compile to binary .mo (required by Flask-Babel at runtime)
pybabel compile -d translations
```

To run these as a single command via Docker:
```bash
docker compose exec frontend sh -c "pybabel extract -F babel.cfg -k _ -o messages.pot . && pybabel update -i messages.pot -d translations && pip install -q polib && python translate.py && pybabel compile -d translations"
```

---

## Seeding Product Data

The `db/` directory contains SQL scripts with pre-loaded product data organized by category. To seed product data into a running database:

```bash
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/abarrotes.sql
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/PROTEINAS.SQL
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/panaderia.sql
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/pasteleria.sql
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/lacteos.sql
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/pulpas.sql
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/preparados.sql
docker compose exec db mysql -u api_user -papipassword requisitions_db < db/aseo-empaques.sql
```

> [!NOTE]
> Product groups must exist in the database before running the product seed scripts. Create them first via the Admin Dashboard or ensure `init.sql` includes them.