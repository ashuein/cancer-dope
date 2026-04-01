"""BAM/CRAM metadata validator.

Does not parse the binary contents — checks file existence, extension,
and presence of an index file (.bai/.crai).
"""

from pathlib import Path

from backend.models.inputs import InputValidationResult, ValidationIssue, InputType

_INDEX_EXTENSIONS = {
    ".bam": [".bam.bai", ".bai"],
    ".cram": [".cram.crai", ".crai"],
}


def validate_bam(path: Path) -> InputValidationResult:
    """Validate BAM/CRAM file presence and index pairing."""
    suffix = path.suffix.lower()
    input_type = InputType.CRAM if suffix == ".cram" else InputType.BAM
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=input_type, filename=path.name, valid=False, issues=issues,
        )

    if suffix not in (".bam", ".cram"):
        issues.append(ValidationIssue(
            field="extension",
            message=f"Expected .bam or .cram, got {suffix}",
            severity="error",
        ))

    summary["format"] = suffix.lstrip(".")
    summary["size_bytes"] = path.stat().st_size

    # Check for index
    index_exts = _INDEX_EXTENSIONS.get(suffix, [])
    index_found = False
    for ext in index_exts:
        candidate = path.with_suffix("") if ext.startswith(".bam") or ext.startswith(".cram") else path
        index_path = path.parent / (path.stem + ext) if not ext.startswith(suffix) else Path(str(path) + ext.replace(suffix, ""))

        # Try common patterns
        for idx_path in [path.parent / (path.name + ".bai"),
                         path.parent / (path.name + ".crai"),
                         path.with_suffix(".bai"),
                         path.with_suffix(".crai")]:
            if idx_path.is_file():
                index_found = True
                summary["index_path"] = str(idx_path)
                break
        if index_found:
            break

    if not index_found:
        issues.append(ValidationIssue(
            field="index", message="No index file (.bai/.crai) found", severity="warning",
        ))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=input_type, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )
