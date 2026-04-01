"""Parser registry — routes input types to their validators."""

from pathlib import Path

from backend.models.inputs import InputType, InputValidationResult, ValidationIssue
from backend.parsers.anndata import validate_anndata, validate_zarr
from backend.parsers.bam import validate_bam
from backend.parsers.expression import validate_expression
from backend.parsers.hla import validate_hla
from backend.parsers.manifest import validate_json_manifest, validate_parquet
from backend.parsers.seg import validate_seg
from backend.parsers.spatial import validate_image_manifest, validate_spatial_bundle
from backend.parsers.vcf import validate_vcf


def validate_input(path: Path, input_type: InputType) -> InputValidationResult:
    """Dispatch to the appropriate validator for the given input type."""
    match input_type:
        case InputType.VCF:
            return validate_vcf(path)
        case InputType.HLA:
            return validate_hla(path)
        case InputType.RNA_COUNTS:
            return validate_expression(path, input_type=InputType.RNA_COUNTS)
        case InputType.RNA_TPM:
            return validate_expression(path, input_type=InputType.RNA_TPM)
        case InputType.SEG:
            return validate_seg(path)
        case InputType.BAM | InputType.CRAM:
            return validate_bam(path)
        case InputType.JSON_MANIFEST:
            return validate_json_manifest(path)
        case InputType.PARQUET:
            return validate_parquet(path)
        case InputType.CLINICAL_CSV:
            from backend.parsers.clinical import validate_clinical_csv
            return validate_clinical_csv(path)
        case InputType.CLINICAL_JSON:
            from backend.parsers.clinical import validate_clinical_json
            return validate_clinical_json(path)
        case InputType.ANNDATA:
            return validate_anndata(path)
        case InputType.ZARR:
            return validate_zarr(path)
        case InputType.IMAGE_MANIFEST:
            return validate_image_manifest(path)
        case InputType.SPATIAL_BUNDLE:
            return validate_spatial_bundle(path)
        case _:
            return InputValidationResult(
                input_type=input_type, filename=path.name, valid=False,
                issues=[ValidationIssue(
                    field="input_type", message=f"No validator for type: {input_type}", severity="error",
                )],
            )
