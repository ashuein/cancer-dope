"""Tests for health and version endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_version_endpoint(client: AsyncClient):
    response = await client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["app"] == "PrecisionOncology"


@pytest.mark.asyncio
async def test_modules_endpoint(client: AsyncClient):
    response = await client.get("/modules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("name" in m and "enabled" in m for m in data)
