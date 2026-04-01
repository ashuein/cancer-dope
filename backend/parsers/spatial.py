"""Spatial bundle and image manifest validators."""

import json
from pathlib import Path

from backend.models.inputs import InputType, InputValidationResult, ValidationIssue


def validate_image_manifest(path: Path) -> InputValidationResult:
    """Validate an image tile manifest (JSON with required fields)."""
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.IMAGE_MANIFEST, filename=path.name, valid=False, issues=issues,
        )

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        issues.append(ValidationIssue(field="file", message=f"Invalid JSON: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.IMAGE_MANIFEST, filename=path.name, valid=False, issues=issues,
        )

    if not isinstance(data, (dict, list)):
        issues.append(ValidationIssue(
            field="root", message="Expected a JSON object or array", severity="error",
        ))
    elif isinstance(data, dict):
        summary["top_level_keys"] = list(data.keys())
        # Check for common image manifest fields
        if "images" in data and isinstance(data["images"], list):
            summary["image_count"] = len(data["images"])
        elif "tiles" in data and isinstance(data["tiles"], list):
            summary["tile_count"] = len(data["tiles"])
        else:
            issues.append(ValidationIssue(
                field="structure",
                message="Expected 'images' or 'tiles' array in manifest",
                severity="warning",
            ))
    elif isinstance(data, list):
        summary["entry_count"] = len(data)

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.IMAGE_MANIFEST, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )


def validate_spatial_bundle(path: Path) -> InputValidationResult:
    """Validate a spatial bundle directory (e.g. Xenium-style output)."""
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.exists():
        issues.append(ValidationIssue(field="path", message="Path not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.SPATIAL_BUNDLE, filename=path.name, valid=False, issues=issues,
        )

    if path.is_file():
        # Could be a single archive — check extension
        if path.suffix.lower() in (".zip", ".tar", ".gz", ".tgz"):
            summary["type"] = "archive"
            summary["size_bytes"] = path.stat().st_size
        else:
            issues.append(ValidationIssue(
                field="format",
                message="Spatial bundle should be a directory or archive (.zip/.tar.gz)",
                severity="error",
            ))
    elif path.is_dir():
        contents = list(path.iterdir())
        summary["type"] = "directory"
        summary["file_count"] = len(contents)
        summary["files"] = [f.name for f in contents[:20]]

        if not contents:
            issues.append(ValidationIssue(
                field="contents", message="Spatial bundle directory is empty", severity="error",
            ))
    else:
        issues.append(ValidationIssue(field="path", message="Not a file or directory", severity="error"))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.SPATIAL_BUNDLE, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )
