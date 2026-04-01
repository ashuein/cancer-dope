"""Integration tests for input registration routes."""

import io
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.repositories import CaseRepository


FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.mark.asyncio
async def test_upload_vcf(client: AsyncClient):
    """Upload a VCF file via the upload endpoint."""
    case_resp = await client.post("/cases", json={"label": "Upload Case"})
    case_id = case_resp.json()["id"]

    vcf_content = (FIXTURES / "sample.vcf").read_bytes()

    resp = await client.post(
        f"/cases/{case_id}/inputs/upload",
        params={"input_type": "vcf"},
        files={"file": ("test.vcf", io.BytesIO(vcf_content), "application/octet-stream")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["input_type"] == "vcf"
    assert data["record_count"] == 3

    # Verify it shows up in summary
    summary = await client.get(f"/cases/{case_id}/inputs/summary")
    sdata = summary.json()
    assert "vcf" in sdata["registered_types"]
    assert sdata["file_count"] == 1


@pytest.mark.asyncio
async def test_upload_case_not_found(client: AsyncClient):
    """Upload to non-existent case returns 404."""
    resp = await client.post(
        "/cases/99999/inputs/upload",
        params={"input_type": "vcf"},
        files={"file": ("test.vcf", io.BytesIO(b"data"), "application/octet-stream")},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_input_summary_empty_case(client: AsyncClient):
    """A case with no inputs should show no registered types and no module readiness."""
    resp = await client.post("/cases", json={"label": "Empty Input Case"})
    case_id = resp.json()["id"]

    summary = await client.get(f"/cases/{case_id}/inputs/summary")
    assert summary.status_code == 200
    data = summary.json()
    assert data["case_id"] == case_id
    assert data["registered_types"] == []
    assert data["file_count"] == 0


@pytest.mark.asyncio
async def test_input_summary_not_found(client: AsyncClient):
    """Input summary for non-existent case returns 404."""
    resp = await client.get("/cases/99999/inputs/summary")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_register_input_from_path(client: AsyncClient, db_session: AsyncSession):
    """Register an input file from an existing path and verify it appears in the summary."""
    case_resp = await client.post("/cases", json={"label": "Register Case"})
    case_id = case_resp.json()["id"]

    # Copy fixture to a temp location
    tmp = Path(tempfile.mkdtemp())
    vcf_path = tmp / "test.vcf"
    shutil.copy(FIXTURES / "sample.vcf", vcf_path)

    try:
        resp = await client.post(
            f"/cases/{case_id}/inputs/register",
            json={
                "inputs": [
                    {"input_type": "vcf", "filename": "test.vcf", "path": str(vcf_path)},
                ]
            },
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["valid"] is True
        assert results[0]["input_type"] == "vcf"
        assert results[0]["record_count"] == 3

        # Check summary
        summary = await client.get(f"/cases/{case_id}/inputs/summary")
        data = summary.json()
        assert "vcf" in data["registered_types"]
        assert data["file_count"] == 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_register_invalid_input(client: AsyncClient):
    """Register an input with a nonexistent path — should validate but report errors."""
    case_resp = await client.post("/cases", json={"label": "Invalid Input Case"})
    case_id = case_resp.json()["id"]

    resp = await client.post(
        f"/cases/{case_id}/inputs/register",
        json={
            "inputs": [
                {"input_type": "vcf", "filename": "missing.vcf", "path": "/nonexistent/missing.vcf"},
            ]
        },
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 1
    assert results[0]["valid"] is False


@pytest.mark.asyncio
async def test_register_mixed_inputs(client: AsyncClient):
    """Register multiple inputs of different types in one batch."""
    case_resp = await client.post("/cases", json={"label": "Mixed Input Case"})
    case_id = case_resp.json()["id"]

    tmp = Path(tempfile.mkdtemp())
    vcf_path = tmp / "test.vcf"
    hla_path = tmp / "test_hla.json"
    expr_path = tmp / "test_expr.tsv"
    shutil.copy(FIXTURES / "sample.vcf", vcf_path)
    shutil.copy(FIXTURES / "sample_hla.json", hla_path)
    shutil.copy(FIXTURES / "sample_expression.tsv", expr_path)

    try:
        resp = await client.post(
            f"/cases/{case_id}/inputs/register",
            json={
                "inputs": [
                    {"input_type": "vcf", "filename": "test.vcf", "path": str(vcf_path)},
                    {"input_type": "hla", "filename": "test_hla.json", "path": str(hla_path)},
                    {"input_type": "rna_tpm", "filename": "test_expr.tsv", "path": str(expr_path)},
                ]
            },
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 3
        assert all(r["valid"] for r in results)

        # Check summary reflects all three types
        summary = await client.get(f"/cases/{case_id}/inputs/summary")
        data = summary.json()
        assert set(data["registered_types"]) == {"vcf", "hla", "rna_tpm"}
        assert data["file_count"] == 3

        # Track 1 requires VCF + HLA — should be ready
        assert data["module_readiness"]["track1"] is True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_register_missing_path(client: AsyncClient):
    """Registration without a path should report an error."""
    case_resp = await client.post("/cases", json={"label": "No Path Case"})
    case_id = case_resp.json()["id"]

    resp = await client.post(
        f"/cases/{case_id}/inputs/register",
        json={
            "inputs": [
                {"input_type": "vcf", "filename": "test.vcf"},
            ]
        },
    )
    assert resp.status_code == 200
    results = resp.json()
    assert results[0]["valid"] is False


@pytest.mark.asyncio
async def test_register_zarr_directory(client: AsyncClient):
    """Register a Zarr directory — should copy into managed storage."""
    case_resp = await client.post("/cases", json={"label": "Zarr Case"})
    case_id = case_resp.json()["id"]

    # Create a valid zarr directory
    tmp = Path(tempfile.mkdtemp())
    zarr_dir = tmp / "test_store.zarr"
    zarr_dir.mkdir()
    (zarr_dir / ".zgroup").write_text('{"zarr_format": 2}')
    (zarr_dir / "X").mkdir()
    (zarr_dir / "X" / ".zarray").write_text('{"dtype": "float32"}')

    try:
        resp = await client.post(
            f"/cases/{case_id}/inputs/register",
            json={
                "inputs": [
                    {"input_type": "zarr", "filename": "test_store.zarr", "path": str(zarr_dir)},
                ]
            },
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["valid"] is True
        assert results[0]["input_type"] == "zarr"

        # Verify it shows in summary
        summary = await client.get(f"/cases/{case_id}/inputs/summary")
        data = summary.json()
        assert "zarr" in data["registered_types"]

        # Verify the artifact was registered (check via artifacts endpoint)
        arts = await client.get(f"/cases/{case_id}/artifacts")
        art_list = arts.json()
        zarr_arts = [a for a in art_list if a["artifact_type"] == "input_zarr"]
        assert len(zarr_arts) == 1
        assert zarr_arts[0]["format"] == "dir"
        # Path should be under managed storage, not the original tmp location
        assert str(tmp) not in zarr_arts[0]["path"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_register_same_filename_no_collision(client: AsyncClient):
    """Registering two files with the same name should produce unique managed paths."""
    case_resp = await client.post("/cases", json={"label": "Collision Case"})
    case_id = case_resp.json()["id"]

    tmp1 = Path(tempfile.mkdtemp())
    tmp2 = Path(tempfile.mkdtemp())
    # Two different VCF files with the same filename
    vcf1 = tmp1 / "variants.vcf"
    vcf2 = tmp2 / "variants.vcf"
    shutil.copy(FIXTURES / "sample.vcf", vcf1)

    # Create a second VCF with different content
    vcf2.write_text(
        "##fileformat=VCFv4.2\n"
        "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tSAMPLE\n"
        "chr1\t100\t.\tA\tT\t50\tPASS\tDP=10\tGT\t0/1\n"
    )

    try:
        resp1 = await client.post(
            f"/cases/{case_id}/inputs/register",
            json={"inputs": [{"input_type": "vcf", "filename": "variants.vcf", "path": str(vcf1)}]},
        )
        resp2 = await client.post(
            f"/cases/{case_id}/inputs/register",
            json={"inputs": [{"input_type": "vcf", "filename": "variants.vcf", "path": str(vcf2)}]},
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # Both should be valid
        assert resp1.json()[0]["valid"] is True
        assert resp2.json()[0]["valid"] is True

        # Summary should show 2 VCF artifacts
        arts = await client.get(f"/cases/{case_id}/artifacts")
        vcf_arts = [a for a in arts.json() if a["artifact_type"] == "input_vcf"]
        assert len(vcf_arts) == 2

        # Their managed paths should be different
        paths = {a["path"] for a in vcf_arts}
        assert len(paths) == 2, f"Expected unique paths, got: {paths}"
    finally:
        shutil.rmtree(tmp1, ignore_errors=True)
        shutil.rmtree(tmp2, ignore_errors=True)


@pytest.mark.asyncio
async def test_register_copies_to_managed_storage(client: AsyncClient):
    """Registered files should be copied into case inputs dir, not referenced in-place."""
    case_resp = await client.post("/cases", json={"label": "Managed Storage Case"})
    case_id = case_resp.json()["id"]

    tmp = Path(tempfile.mkdtemp())
    vcf_path = tmp / "test.vcf"
    shutil.copy(FIXTURES / "sample.vcf", vcf_path)

    try:
        resp = await client.post(
            f"/cases/{case_id}/inputs/register",
            json={"inputs": [{"input_type": "vcf", "filename": "test.vcf", "path": str(vcf_path)}]},
        )
        assert resp.status_code == 200
        assert resp.json()[0]["valid"] is True

        # Verify artifact path is NOT under the original tmp directory
        arts = await client.get(f"/cases/{case_id}/artifacts")
        for art in arts.json():
            if art["artifact_type"] == "input_vcf":
                assert str(tmp) not in art["path"], "Artifact path should be in managed storage, not source"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_json_manifest_does_not_make_gsea_ready(client: AsyncClient):
    """Regression: a generic JSON manifest should make timeline ready but NOT gsea."""
    case_resp = await client.post("/cases", json={"label": "GSEA Readiness Case"})
    case_id = case_resp.json()["id"]

    tmp = Path(tempfile.mkdtemp())
    manifest_path = tmp / "timeline.json"
    manifest_path.write_text('{"events": [{"date": "2024-01-01", "event_type": "diagnosis"}]}')

    try:
        resp = await client.post(
            f"/cases/{case_id}/inputs/register",
            json={"inputs": [
                {"input_type": "json_manifest", "filename": "timeline.json", "path": str(manifest_path)},
            ]},
        )
        assert resp.status_code == 200
        assert resp.json()[0]["valid"] is True

        summary = await client.get(f"/cases/{case_id}/inputs/summary")
        data = summary.json()
        # JSON manifest is accepted by timeline (as json_manifest is in its optional list)
        assert data["module_readiness"]["timeline"] is True
        # GSEA should NOT be ready — it only accepts parquet, not json_manifest
        assert data["module_readiness"]["gsea"] is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_register_uses_caller_filename(client: AsyncClient):
    """The managed name should be based on the caller-provided filename, not the source basename."""
    case_resp = await client.post("/cases", json={"label": "Filename Case"})
    case_id = case_resp.json()["id"]

    tmp = Path(tempfile.mkdtemp())
    vcf_path = tmp / "original_name.vcf"
    shutil.copy(FIXTURES / "sample.vcf", vcf_path)

    try:
        resp = await client.post(
            f"/cases/{case_id}/inputs/register",
            json={"inputs": [
                {"input_type": "vcf", "filename": "my_custom_name.vcf", "path": str(vcf_path)},
            ]},
        )
        assert resp.status_code == 200
        assert resp.json()[0]["valid"] is True

        arts = await client.get(f"/cases/{case_id}/artifacts")
        vcf_arts = [a for a in arts.json() if a["artifact_type"] == "input_vcf"]
        assert len(vcf_arts) == 1
        # Managed path should contain the caller-provided name, not original_name
        assert "my_custom_name.vcf" in vcf_arts[0]["path"]
        assert "original_name" not in vcf_arts[0]["path"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_register_reports_failure_on_post_validation_error(client: AsyncClient):
    """If registration fails after validation passes, the client should see valid=False."""
    case_resp = await client.post("/cases", json={"label": "Post-Val Fail Case"})
    case_id = case_resp.json()["id"]

    tmp = Path(tempfile.mkdtemp())
    vcf_path = tmp / "test.vcf"
    shutil.copy(FIXTURES / "sample.vcf", vcf_path)

    try:
        # Force path_checksum to fail after the file is copied
        with patch("backend.routers.inputs.path_checksum", side_effect=OSError("disk error")):
            resp = await client.post(
                f"/cases/{case_id}/inputs/register",
                json={"inputs": [
                    {"input_type": "vcf", "filename": "test.vcf", "path": str(vcf_path)},
                ]},
            )
            assert resp.status_code == 200
            results = resp.json()
            assert len(results) == 1
            # Validation passed but registration failed — client must see valid=False
            assert results[0]["valid"] is False
            assert any("registration failed" in i["message"].lower() for i in results[0]["issues"])

        # No artifact should have been registered
        arts = await client.get(f"/cases/{case_id}/artifacts")
        vcf_arts = [a for a in arts.json() if a["artifact_type"] == "input_vcf"]
        assert len(vcf_arts) == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_upload_reports_failure_on_post_validation_error(client: AsyncClient):
    """Upload should report valid=False if post-validation registration fails."""
    case_resp = await client.post("/cases", json={"label": "Upload Fail Case"})
    case_id = case_resp.json()["id"]

    vcf_content = (FIXTURES / "sample.vcf").read_bytes()

    with patch("backend.routers.inputs.path_checksum", side_effect=OSError("disk error")):
        resp = await client.post(
            f"/cases/{case_id}/inputs/upload",
            params={"input_type": "vcf"},
            files={"file": ("test.vcf", io.BytesIO(vcf_content), "application/octet-stream")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is False
        assert any("registration failed" in i["message"].lower() for i in data["issues"])
