"""Integration tests for workflow launch endpoints."""

import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_launch_workflow_dry_run_creates_run_and_returns_command(client: AsyncClient):
    case = await client.post("/cases", json={"label": "Workflow Case"})
    case_id = case.json()["id"]

    response = await client.post(
        f"/workflows/cases/{case_id}/runs",
        json={
            "dry_run": True,
            "params": {"sample_sheet": "/tmp/samples.csv"},
            "profiles": ["docker"],
            "resume": True,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["dry_run"] is True
    assert data["launched"] is False
    assert data["pid"] is None
    assert data["run"]["case_id"] == case_id
    assert data["run"]["status"] == "pending"
    assert data["command"][:2] == ["nextflow", "run"]
    assert "-resume" in data["command"]
    assert "--case_id" in data["command"]
    assert str(case_id) == data["command"][data["command"].index("--case_id") + 1]
    assert "--run_id" in data["command"]
    assert str(data["run"]["id"]) == data["command"][data["command"].index("--run_id") + 1]
    assert "--sample_sheet" in data["command"]

    config_snapshot = json.loads(data["run"]["config_snapshot"])
    assert config_snapshot["dry_run"] is True
    assert config_snapshot["params"]["sample_sheet"] == "/tmp/samples.csv"


@pytest.mark.asyncio
async def test_launch_workflow_case_not_found(client: AsyncClient):
    response = await client.post("/workflows/cases/99999/runs", json={"dry_run": True})

    assert response.status_code == 404
