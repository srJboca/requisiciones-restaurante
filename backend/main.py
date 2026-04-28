from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from routers import auth, admin, requisitions, production

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Restaurant Requisitions API", description="API for Restaurant Chain Requisitions", version="1.0.0")

# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
