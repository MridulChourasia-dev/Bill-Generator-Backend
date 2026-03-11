from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import engine, Base, init_db
from app.api.v1 import auth, bills, payments, reminders, reports

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting up Bill Generator API...")
    # Auto-create all tables (safe for development; use Alembic in production)
    init_db()
    yield
    logger.info("Shutting down Bill Generator API...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## Bill Generator API

    A comprehensive bill management and payment tracking API.

    ### Features
    - 🔐 JWT-based authentication
    - 📄 Bill creation and management
    - 💳 Payment tracking
    - 📧 Email reminders
    - 📱 SMS notifications
    - 📊 Reports & analytics
    - 📑 PDF receipt generation
    """,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(bills.router, prefix="/api/v1/bills", tags=["Bills"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["Payments"])
app.include_router(reminders.router, prefix="/api/v1/reminders", tags=["Reminders"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Bill Generator API is running",
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
    }
