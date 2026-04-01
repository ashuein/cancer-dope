"""Pydantic schemas for the input layer and processed import contracts.

Each module declares what input types it accepts. Inputs can be registered
by file upload or by pointing at an existing path on disk / manifest.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ---------- Input types ----------


class InputType(str, Enum):
    """Canonical input types the platform accepts."""

    VCF = "vcf"
    HLA = "hla"
    RNA_COUNTS = "rna_counts"
    RNA_TPM = "rna_tpm"
    SEG = "seg"
    BAM = "bam"
    CRAM = "cram"
    ANNDATA = "anndata"
    ZARR = "zarr"
    PARQUET = "parquet"
    JSON_MANIFEST = "json_manifest"
    IMAGE_MANIFEST = "image_manifest"
    SPATIAL_BUNDLE = "spatial_bundle"
    CLINICAL_CSV = "clinical_csv"
    CLINICAL_JSON = "clinical_json"


# ---------- Module capability flags ----------


class ModuleInputCapability(BaseModel):
    """Declares what input types a module accepts and which are required vs optional."""

    module: str
    required: list[InputType] = []
    optional: list[InputType] = []


# Module -> accepted inputs mapping
MODULE_CAPABILITIES: list[ModuleInputCapability] = [
    ModuleInputCapability(
        module="timeline",
        required=[],
        optional=[InputType.CLINICAL_CSV, InputType.CLINICAL_JSON, InputType.JSON_MANIFEST],
    ),
    ModuleInputCapability(
        module="track1",
        required=[InputType.VCF, InputType.HLA],
        optional=[InputType.RNA_TPM, InputType.RNA_COUNTS],
    ),
    ModuleInputCapability(
        module="track2",
        required=[InputType.VCF],
        optional=[InputType.SEG, InputType.RNA_TPM],
    ),
    ModuleInputCapability(
        module="bulk_rna",
        required=[],
        optional=[InputType.RNA_COUNTS, InputType.RNA_TPM, InputType.PARQUET],
    ),
    ModuleInputCapability(
        module="scrna",
        required=[],
        optional=[InputType.ANNDATA, InputType.ZARR],
    ),
    ModuleInputCapability(
        module="gsea",
        required=[],
        optional=[InputType.PARQUET],
    ),
    ModuleInputCapability(
        module="cnv",
        required=[],
        optional=[InputType.SEG, InputType.BAM],
    ),
    ModuleInputCapability(
        module="bam",
        required=[],
        optional=[InputType.BAM, InputType.CRAM],
    ),
    ModuleInputCapability(
        module="imaging",
        required=[],
        optional=[InputType.IMAGE_MANIFEST],
    ),
    ModuleInputCapability(
        module="spatial",
        required=[],
        optional=[InputType.SPATIAL_BUNDLE],
    ),
]


def capabilities_for_module(module: str) -> ModuleInputCapability | None:
    for cap in MODULE_CAPABILITIES:
        if cap.module == module:
            return cap
    return None


def modules_accepting(input_type: InputType) -> list[str]:
    """Return module names that accept a given input type (required or optional)."""
    result = []
    for cap in MODULE_CAPABILITIES:
        if input_type in cap.required or input_type in cap.optional:
            result.append(cap.module)
    return result


# ---------- Input manifest ----------


class InputFileEntry(BaseModel):
    """One file in a case input manifest."""

    input_type: InputType
    filename: str
    path: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    metadata: dict = Field(default_factory=dict)


class CaseInputManifest(BaseModel):
    """Manifest describing all inputs registered for a case."""

    case_id: int
    files: list[InputFileEntry] = []


# ---------- Registration request / response ----------


class InputRegistration(BaseModel):
    """Request body for registering an input file."""

    input_type: InputType
    filename: str
    path: str | None = None
    metadata: dict = Field(default_factory=dict)


class InputRegistrationBatch(BaseModel):
    """Register multiple inputs at once."""

    inputs: list[InputRegistration]


class ValidationIssue(BaseModel):
    """One validation problem found in an input file."""

    field: str
    message: str
    severity: Literal["error", "warning"]


class InputValidationResult(BaseModel):
    """Result of validating a single input file."""

    input_type: InputType
    filename: str
    valid: bool
    issues: list[ValidationIssue] = []
    record_count: int | None = None
    summary: dict = Field(default_factory=dict)


class InputSummary(BaseModel):
    """Normalized summary of all registered inputs for a case."""

    case_id: int
    registered_types: list[InputType]
    module_readiness: dict[str, bool]
    file_count: int
    validation_results: list[InputValidationResult] = []
