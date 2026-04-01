"""Tests for input parsers and validators."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from backend.models.inputs import InputType
from backend.parsers.vcf import validate_vcf
from backend.parsers.hla import validate_hla
from backend.parsers.expression import validate_expression
from backend.parsers.seg import validate_seg
from backend.parsers.bam import validate_bam
from backend.parsers.clinical import validate_clinical_csv, validate_clinical_json
from backend.parsers.anndata import validate_anndata, validate_zarr
from backend.parsers.spatial import validate_image_manifest, validate_spatial_bundle
from backend.parsers.manifest import validate_json_manifest
from backend.parsers.registry import validate_input

FIXTURES = Path(__file__).parent.parent / "fixtures"


# ---------- VCF ----------


def test_vcf_valid():
    result = validate_vcf(FIXTURES / "sample.vcf")
    assert result.valid is True
    assert result.record_count == 3
    assert result.summary["vcf_version"] == "4.2"
    assert result.summary["sample_count"] == 2


def test_vcf_missing_file():
    result = validate_vcf(Path("/nonexistent/file.vcf"))
    assert result.valid is False
    assert any("not found" in i.message.lower() for i in result.issues)


def test_vcf_empty_file():
    with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False, mode="w") as f:
        path = Path(f.name)
    try:
        result = validate_vcf(path)
        assert result.valid is False
    finally:
        path.unlink(missing_ok=True)


def test_vcf_missing_header():
    with tempfile.NamedTemporaryFile(suffix=".vcf", delete=False, mode="w") as f:
        f.write("chr1\t100\t.\tA\tT\t50\tPASS\t.\n")
        path = Path(f.name)
    try:
        result = validate_vcf(path)
        assert result.valid is False
    finally:
        path.unlink(missing_ok=True)


# ---------- HLA ----------


def test_hla_valid():
    result = validate_hla(FIXTURES / "sample_hla.json")
    assert result.valid is True
    assert result.summary["class_i_alleles"] == 6
    assert result.summary["source"] == "manual"


def test_hla_invalid_json():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        f.write("not json {{{")
        path = Path(f.name)
    try:
        result = validate_hla(path)
        assert result.valid is False
    finally:
        path.unlink(missing_ok=True)


def test_hla_invalid_allele_format():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({"class_i": {"HLA-A": ["BADFORMAT"]}}, f)
        path = Path(f.name)
    try:
        result = validate_hla(path)
        assert result.valid is False
        assert any("invalid allele" in i.message.lower() for i in result.issues)
    finally:
        path.unlink(missing_ok=True)


# ---------- Expression ----------


def test_expression_valid():
    result = validate_expression(FIXTURES / "sample_expression.tsv")
    assert result.valid is True
    assert result.record_count == 5


def test_expression_missing_gene_columns():
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False, mode="w") as f:
        f.write("value\n1.0\n2.0\n")
        path = Path(f.name)
    try:
        result = validate_expression(path)
        assert result.valid is False
    finally:
        path.unlink(missing_ok=True)


def test_expression_non_numeric():
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False, mode="w") as f:
        f.write("gene_id\tgene_name\ttpm\nENSG1\tFOO\tnot_a_number\n")
        path = Path(f.name)
    try:
        result = validate_expression(path)
        assert result.valid is False
    finally:
        path.unlink(missing_ok=True)


# ---------- SEG ----------


def test_seg_valid():
    result = validate_seg(FIXTURES / "sample_seg.tsv")
    assert result.valid is True
    assert result.record_count == 4
    assert result.summary["segment_count"] == 4


def test_seg_missing_columns():
    with tempfile.NamedTemporaryFile(suffix=".tsv", delete=False, mode="w") as f:
        f.write("col_a\tcol_b\n1\t2\n")
        path = Path(f.name)
    try:
        result = validate_seg(path)
        assert result.valid is False
        assert any("missing required" in i.message.lower() for i in result.issues)
    finally:
        path.unlink(missing_ok=True)


def test_seg_missing_file():
    result = validate_seg(Path("/nonexistent/file.seg"))
    assert result.valid is False


# ---------- BAM ----------


def test_bam_missing_file():
    result = validate_bam(Path("/nonexistent/file.bam"))
    assert result.valid is False


def test_bam_wrong_extension():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"not a bam")
        path = Path(f.name)
    try:
        result = validate_bam(path)
        assert result.valid is False
        assert any("expected .bam or .cram" in i.message.lower() for i in result.issues)
    finally:
        path.unlink(missing_ok=True)


def test_bam_valid_without_index():
    with tempfile.NamedTemporaryFile(suffix=".bam", delete=False) as f:
        f.write(b"fake bam content")
        path = Path(f.name)
    try:
        result = validate_bam(path)
        assert result.valid is True
        assert any("no index" in i.message.lower() for i in result.issues)
    finally:
        path.unlink(missing_ok=True)


# ---------- Clinical ----------


def test_clinical_csv_valid():
    result = validate_clinical_csv(FIXTURES / "sample_clinical.csv")
    assert result.valid is True
    assert result.record_count == 7
    assert "date" in result.summary.get("date_columns", [])
    assert "event_type" in result.summary.get("event_columns", [])


def test_clinical_csv_no_date_column():
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        f.write("name,value\nfoo,1\nbar,2\n")
        path = Path(f.name)
    try:
        result = validate_clinical_csv(path)
        assert result.valid is True  # warnings only
        assert any("no date column" in i.message.lower() for i in result.issues)
    finally:
        path.unlink(missing_ok=True)


def test_clinical_json_valid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump([
            {"date": "2024-01-01", "event_type": "diagnosis", "description": "test"},
            {"date": "2024-02-01", "event_type": "treatment", "description": "chemo"},
        ], f)
        path = Path(f.name)
    try:
        result = validate_clinical_json(path)
        assert result.valid is True
        assert result.summary.get("record_count") == 2
    finally:
        path.unlink(missing_ok=True)


def test_clinical_csv_missing_file():
    result = validate_clinical_csv(Path("/nonexistent/file.csv"))
    assert result.valid is False


# ---------- AnnData ----------


def test_anndata_missing_file():
    result = validate_anndata(Path("/nonexistent/file.h5ad"))
    assert result.valid is False


def test_anndata_not_hdf5():
    with tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False) as f:
        f.write(b"this is not hdf5")
        path = Path(f.name)
    try:
        result = validate_anndata(path)
        assert result.valid is False
        assert any("hdf5" in i.message.lower() for i in result.issues)
    finally:
        path.unlink(missing_ok=True)


def test_anndata_magic_only_is_not_valid():
    """A file with just HDF5 magic bytes should fail structure validation (if h5py is available)
    or produce a warning (if h5py is not installed)."""
    with tempfile.NamedTemporaryFile(suffix=".h5ad", delete=False) as f:
        f.write(b"\x89HDF\r\n\x1a\n" + b"\x00" * 100)
        path = Path(f.name)
    try:
        result = validate_anndata(path)
        assert result.summary.get("format") == "h5ad"
        # With h5py: should be invalid (corrupt structure)
        # Without h5py: valid=True but with a dependency warning
        has_h5py_warning = any("h5py not installed" in i.message for i in result.issues)
        if not has_h5py_warning:
            # h5py is available — junk file should be rejected
            assert result.valid is False
    finally:
        path.unlink(missing_ok=True)


# ---------- Zarr ----------


def test_zarr_missing_path():
    result = validate_zarr(Path("/nonexistent/zarr_store"))
    assert result.valid is False


def test_zarr_not_a_directory():
    with tempfile.NamedTemporaryFile(suffix=".zarr", delete=False) as f:
        f.write(b"not a directory")
        path = Path(f.name)
    try:
        result = validate_zarr(path)
        assert result.valid is False
        assert any("directory" in i.message.lower() for i in result.issues)
    finally:
        path.unlink(missing_ok=True)


def test_zarr_missing_markers():
    tmpdir = Path(tempfile.mkdtemp(suffix=".zarr"))
    try:
        result = validate_zarr(tmpdir)
        assert result.valid is False
        assert any(".zgroup" in i.message for i in result.issues)
    finally:
        os.rmdir(tmpdir)


def test_zarr_valid_with_zgroup():
    tmpdir = Path(tempfile.mkdtemp(suffix=".zarr"))
    (tmpdir / ".zgroup").write_text('{"zarr_format": 2}')
    try:
        result = validate_zarr(tmpdir)
        assert result.valid is True
        assert result.summary.get("is_group") is True
    finally:
        (tmpdir / ".zgroup").unlink()
        os.rmdir(tmpdir)


# ---------- Spatial ----------


def test_image_manifest_valid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({"images": [{"url": "tile1.png"}, {"url": "tile2.png"}]}, f)
        path = Path(f.name)
    try:
        result = validate_image_manifest(path)
        assert result.valid is True
        assert result.summary.get("image_count") == 2
    finally:
        path.unlink(missing_ok=True)


def test_image_manifest_missing_images():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({"metadata": "no images here"}, f)
        path = Path(f.name)
    try:
        result = validate_image_manifest(path)
        assert result.valid is True
        assert any("images" in i.message.lower() or "tiles" in i.message.lower() for i in result.issues)
    finally:
        path.unlink(missing_ok=True)


def test_spatial_bundle_empty_dir():
    tmpdir = Path(tempfile.mkdtemp(suffix="_spatial"))
    try:
        result = validate_spatial_bundle(tmpdir)
        assert result.valid is False
        assert any("empty" in i.message.lower() for i in result.issues)
    finally:
        os.rmdir(tmpdir)


def test_spatial_bundle_valid_dir():
    tmpdir = Path(tempfile.mkdtemp(suffix="_spatial"))
    (tmpdir / "cells.csv").write_text("x,y,gene\n1,2,EGFR\n")
    try:
        result = validate_spatial_bundle(tmpdir)
        assert result.valid is True
        assert result.summary.get("file_count") == 1
    finally:
        (tmpdir / "cells.csv").unlink()
        os.rmdir(tmpdir)


# ---------- JSON manifest ----------


def test_json_manifest_valid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({"key": "value", "items": [1, 2, 3]}, f)
        path = Path(f.name)
    try:
        result = validate_json_manifest(path)
        assert result.valid is True
    finally:
        path.unlink(missing_ok=True)


def test_json_manifest_invalid():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        f.write("{{invalid json")
        path = Path(f.name)
    try:
        result = validate_json_manifest(path)
        assert result.valid is False
    finally:
        path.unlink(missing_ok=True)


# ---------- Registry dispatch ----------


def test_registry_dispatches_correctly():
    result = validate_input(FIXTURES / "sample.vcf", InputType.VCF)
    assert result.valid is True
    assert result.input_type == InputType.VCF

    result = validate_input(FIXTURES / "sample_hla.json", InputType.HLA)
    assert result.valid is True
    assert result.input_type == InputType.HLA

    result = validate_input(FIXTURES / "sample_expression.tsv", InputType.RNA_TPM)
    assert result.valid is True
    assert result.input_type == InputType.RNA_TPM

    result = validate_input(FIXTURES / "sample_seg.tsv", InputType.SEG)
    assert result.valid is True
    assert result.input_type == InputType.SEG

    result = validate_input(FIXTURES / "sample_clinical.csv", InputType.CLINICAL_CSV)
    assert result.valid is True
    assert result.input_type == InputType.CLINICAL_CSV
