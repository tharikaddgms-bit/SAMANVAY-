import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import PROJECT_NAME, VERSION, API_V1_STR
from app.core.security import init_ed25519_keys
from app.db.database import init_db, get_db
from app.db.seed_data import seed_database

# Routers
from app.api.auth import router as auth_router
from app.api.students import router as students_router
from app.api.reconciliation import router as reconciliation_router
from app.api.duplicates import router as duplicates_router
from app.api.credentials import router as credentials_router
from app.api.audit import router as audit_router
from app.api.dashboard import router as dashboard_router
from app.api.demo import router as demo_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("samanvay")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Keys, DB Schema, and Seed Data if needed
    logger.info("Initializing SAMANVAY backend...")
    init_ed25519_keys()
    init_db()

    # Check if student records exist; if not, auto-seed
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM students;")
        count = cursor.fetchone()[0]
        if count == 0:
            logger.info("Database empty. Seeding synthetic demonstration dataset...")
            seed_database(reset=False)
            logger.info("Synthetic demonstration dataset seeded successfully.")

    yield
    logger.info("Shutting down SAMANVAY backend.")

app = FastAPI(
    title=f"{PROJECT_NAME} API - SIH 2026",
    version=VERSION,
    description="Privacy-Conscious Student Data Management and Verification Platform for AICTE-Approved Institutions",
    lifespan=lifespan,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local hackathon demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=API_V1_STR)
app.include_router(students_router, prefix=API_V1_STR)
app.include_router(reconciliation_router, prefix=API_V1_STR)
app.include_router(duplicates_router, prefix=API_V1_STR)
app.include_router(credentials_router, prefix=API_V1_STR)
app.include_router(audit_router, prefix=API_V1_STR)
app.include_router(dashboard_router, prefix=API_V1_STR)
app.include_router(demo_router, prefix=API_V1_STR)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": PROJECT_NAME,
        "version": VERSION,
        "mode": "DEMO_MODE",
    }
