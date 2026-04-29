import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, admin, requisitions, production

# Create database tables
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# CORS — origins are configured via the ALLOWED_ORIGINS environment variable
# (comma-separated). Falls back to localhost defaults for local development.
# In Azure, set ALLOWED_ORIGINS to the frontend App Service URL, e.g.:
#   https://lacesta-frontend.azurewebsites.net
# ---------------------------------------------------------------------------
_default_origins = [
    "http://localhost:5000",
    "http://localhost:5001"
]

_env_origins = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else _default_origins
)

app = FastAPI(title="Restaurant Requisitions API", description="API for Restaurant Chain Requisitions", version="1.0.0")

# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(requisitions.router)
app.include_router(production.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Restaurant Requisitions API. See /docs for Swagger UI."}
