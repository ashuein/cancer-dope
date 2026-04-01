"""Tests for case and run CRUD endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_case(client: AsyncClient):
    response = await client.post("/cases", json={"label": "Test Patient"})
    assert response.status_code == 201
    data = response.json()
    assert data["label"] == "Test Patient"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_cases_empty(client: AsyncClient):
    response = await client.get("/cases")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_case(client: AsyncClient):
    create = await client.post("/cases", json={"label": "Case A"})
    case_id = create.json()["id"]
    response = await client.get(f"/cases/{case_id}")
    assert response.status_code == 200
    assert response.json()["label"] == "Case A"


@pytest.mark.asyncio
async def test_get_case_not_found(client: AsyncClient):
    response = await client.get("/cases/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_run(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Case B"})
    case_id = case.json()["id"]
    response = await client.post(f"/cases/{case_id}/runs", json={})
    assert response.status_code == 201
    data = response.json()
    assert data["case_id"] == case_id
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_runs(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Case C"})
    case_id = case.json()["id"]
    await client.post(f"/cases/{case_id}/runs", json={})
    await client.post(f"/cases/{case_id}/runs", json={})
    response = await client.get(f"/cases/{case_id}/runs")
    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_list_steps_empty(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Case D"})
    case_id = case.json()["id"]
    run = await client.post(f"/cases/{case_id}/runs", json={})
    run_id = run.json()["id"]
    response = await client.get(f"/cases/{case_id}/runs/{run_id}/steps")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_case_artifacts_empty(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Case E"})
    case_id = case.json()["id"]
    response = await client.get(f"/cases/{case_id}/artifacts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_update_case(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Old Label"})
    case_id = case.json()["id"]
    response = await client.patch(f"/cases/{case_id}", json={"label": "New Label"})
    assert response.status_code == 200
    assert response.json()["label"] == "New Label"


@pytest.mark.asyncio
async def test_update_case_not_found(client: AsyncClient):
    response = await client.patch("/cases/999", json={"label": "X"})
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_case(client: AsyncClient):
    case = await client.post("/cases", json={"label": "To Delete"})
    case_id = case.json()["id"]
    response = await client.delete(f"/cases/{case_id}")
    assert response.status_code == 204
    get_response = await client.get(f"/cases/{case_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_case_not_found(client: AsyncClient):
    response = await client.delete("/cases/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_run(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Case F"})
    case_id = case.json()["id"]
    run = await client.post(f"/cases/{case_id}/runs", json={})
    run_id = run.json()["id"]
    response = await client.patch(
        f"/cases/{case_id}/runs/{run_id}", json={"status": "running"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "running"


@pytest.mark.asyncio
async def test_update_run_invalid_status(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Case F2"})
    case_id = case.json()["id"]
    run = await client.post(f"/cases/{case_id}/runs", json={})
    run_id = run.json()["id"]
    response = await client.patch(
        f"/cases/{case_id}/runs/{run_id}", json={"status": "bogus_state"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_run(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Case G"})
    case_id = case.json()["id"]
    run = await client.post(f"/cases/{case_id}/runs", json={})
    run_id = run.json()["id"]
    response = await client.delete(f"/cases/{case_id}/runs/{run_id}")
    assert response.status_code == 204
