"""Database engine and session management."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config.settings import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,
    connect_args={"check_same_thread": False},
)

_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Overridable session factory — tests replace this to point at an in-memory DB.
_session_factory_override: async_sessionmaker | None = None


def set_session_factory_override(factory: async_sessionmaker | None) -> None:
    """Override the session factory (used by tests to inject an in-memory DB)."""
    global _session_factory_override
    _session_factory_override = factory


def _get_factory() -> async_sessionmaker:
    return _session_factory_override or _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a database session."""
    async with _get_factory()() as session:
        yield session


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for code that can't use FastAPI Depends (e.g. WebSocket, workers).

    Uses the same (possibly overridden) session factory as get_db.
    """
    async with _get_factory()() as session:
        yield session
