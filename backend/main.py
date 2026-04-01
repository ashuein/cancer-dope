"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import settings
from backend.db.database import engine
from backend.db.models import Base
from backend.middleware.errors import ErrorHandlerMiddleware
from backend.routers import artifacts, cases, health, inputs, ws

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    logger.info("Starting %s (%s)", settings.app_name, settings.app_env)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")
    yield
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# Middleware
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(cases.router)
app.include_router(artifacts.router)
app.include_router(inputs.router)
app.include_router(ws.router)
