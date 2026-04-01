"""JSON and Parquet manifest validators.

These validate structural integrity of manifest files — the actual
content schema depends on the module that consumes them.
"""

import json
from pathlib import Path

from backend.models.inputs import InputValidationResult, ValidationIssue, InputType


def validate_json_manifest(path: Path) -> InputValidationResult:
    """Validate a JSON manifest file."""
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.JSON_MANIFEST, filename=path.name, valid=False, issues=issues,
        )

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        issues.append(ValidationIssue(field="file", message=f"Invalid JSON: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.JSON_MANIFEST, filename=path.name, valid=False, issues=issues,
        )

    if isinstance(data, dict):
        summary["top_level_keys"] = list(data.keys())
        summary["type"] = "object"
    elif isinstance(data, list):
        summary["record_count"] = len(data)
        summary["type"] = "array"
    else:
        issues.append(ValidationIssue(
            field="root", message="Expected a JSON object or array", severity="error",
        ))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.JSON_MANIFEST, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )


def validate_parquet(path: Path) -> InputValidationResult:
    """Validate a Parquet file by reading its metadata."""
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.PARQUET, filename=path.name, valid=False, issues=issues,
        )

    try:
        import pyarrow.parquet as pq

        pf = pq.ParquetFile(path)
        metadata = pf.metadata
        summary["num_rows"] = metadata.num_rows
        summary["num_columns"] = metadata.num_columns
        summary["columns"] = [pf.schema_arrow.field(i).name for i in range(metadata.num_columns)]
    except ImportError:
        issues.append(ValidationIssue(
            field="dependency", message="pyarrow not installed — cannot validate parquet", severity="warning",
        ))
    except Exception as e:
        issues.append(ValidationIssue(field="file", message=f"Cannot read parquet: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.PARQUET, filename=path.name, valid=False, issues=issues,
        )

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.PARQUET, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )
