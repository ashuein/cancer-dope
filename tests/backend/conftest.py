"""Shared test fixtures for backend tests."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.models import Base
from backend.db.database import get_db, set_session_factory_override
from backend.main import app


@pytest_asyncio.fixture
async def db_session():
    """Create an in-memory SQLite database for testing.

    Overrides both the FastAPI get_db dependency and the session factory
    used by code that can't use Depends (WebSocket routes, workers).
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Override the global session factory so get_session() in ws.py uses the test DB
    set_session_factory_override(session_factory)

    async with session_factory() as session:
        yield session

    set_session_factory_override(None)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """Create a test client with overridden database dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
