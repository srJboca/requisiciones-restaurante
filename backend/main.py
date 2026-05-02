import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, admin, requisitions, production, superadmin, nps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

_default_origins = [
    "http://localhost:5000",
    "http://localhost:5001",
]
_env_origins = os.environ.get("ALLOWED_ORIGINS", "")
allowed_origins = (
    [o.strip() for o in _env_origins.split(",") if o.strip()]
    if _env_origins
    else _default_origins
)

app = FastAPI(
    title="Restaurant Requisitions API",
    description="Multi-company restaurant requisition management system",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(superadmin.router)
app.include_router(admin.router)
app.include_router(requisitions.router)
app.include_router(production.router)
app.include_router(nps.router)

@app.get("/")
def read_root():
    return {"message": "Restaurant Requisitions API v2.0 — Multi-Company. See /docs for Swagger UI."}
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Backend is awake and ready"}
