"""SEG file parser and validator for copy number segments."""

import csv
from pathlib import Path

from backend.models.inputs import InputValidationResult, ValidationIssue, InputType

_SEG_REQUIRED = {"ID", "chrom", "loc.start", "loc.end", "num.mark", "seg.mean"}
_SEG_ALT_REQUIRED = {"Sample", "Chromosome", "Start", "End", "Num_Probes", "Segment_Mean"}


def validate_seg(path: Path) -> InputValidationResult:
    """Validate a SEG file (tab-separated copy number segments)."""
    issues: list[ValidationIssue] = []
    summary: dict = {}
    record_count = 0

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.SEG, filename=path.name, valid=False, issues=issues,
        )

    try:
        with open(path, "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            if reader.fieldnames is None:
                issues.append(ValidationIssue(
                    field="header", message="No header row found", severity="error",
                ))
                return InputValidationResult(
                    input_type=InputType.SEG, filename=path.name, valid=False, issues=issues,
                )

            headers = set(reader.fieldnames)
            summary["columns"] = list(reader.fieldnames)

            # Accept either standard or alternative column naming
            if not (_SEG_REQUIRED <= headers or _SEG_ALT_REQUIRED <= headers):
                issues.append(ValidationIssue(
                    field="columns",
                    message=f"Missing required columns. Expected one of: {_SEG_REQUIRED} or {_SEG_ALT_REQUIRED}",
                    severity="error",
                ))

            for row in reader:
                record_count += 1

    except Exception as e:
        issues.append(ValidationIssue(field="file", message=f"Cannot parse file: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.SEG, filename=path.name, valid=False, issues=issues,
        )

    summary["segment_count"] = record_count
    if record_count == 0:
        issues.append(ValidationIssue(field="records", message="No segments found", severity="warning"))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.SEG, filename=path.name,
        valid=valid, issues=issues, record_count=record_count, summary=summary,
    )
