"""VCF file parser and validator."""

import re
from pathlib import Path

from backend.models.inputs import InputValidationResult, ValidationIssue, InputType

_VCF_HEADER_RE = re.compile(r"^##fileformat=VCFv(\d+\.\d+)")
_REQUIRED_COLUMNS = {"#CHROM", "POS", "ID", "REF", "ALT", "QUAL", "FILTER", "INFO"}


def validate_vcf(path: Path) -> InputValidationResult:
    """Validate a VCF file. Returns validation result with issues and record count."""
    issues: list[ValidationIssue] = []
    record_count = 0
    summary: dict = {}

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.VCF, filename=path.name,
            valid=False, issues=issues,
        )

    try:
        with open(path, "r") as f:
            lines = f.readlines()
    except Exception as e:
        issues.append(ValidationIssue(field="file", message=f"Cannot read file: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.VCF, filename=path.name,
            valid=False, issues=issues,
        )

    if not lines:
        issues.append(ValidationIssue(field="file", message="File is empty", severity="error"))
        return InputValidationResult(
            input_type=InputType.VCF, filename=path.name,
            valid=False, issues=issues,
        )

    # Check fileformat header
    first_line = lines[0].strip()
    match = _VCF_HEADER_RE.match(first_line)
    if not match:
        issues.append(ValidationIssue(
            field="header", message="Missing or invalid ##fileformat line", severity="error",
        ))
    else:
        summary["vcf_version"] = match.group(1)

    # Find column header line
    header_line = None
    header_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("#CHROM"):
            header_line = line.strip()
            header_idx = i
            break

    if header_line is None:
        issues.append(ValidationIssue(
            field="header", message="Missing #CHROM column header line", severity="error",
        ))
    else:
        columns = set(header_line.split("\t"))
        missing = _REQUIRED_COLUMNS - columns
        if missing:
            issues.append(ValidationIssue(
                field="columns",
                message=f"Missing required columns: {', '.join(sorted(missing))}",
                severity="error",
            ))

        # Count sample columns (everything after FORMAT)
        all_cols = header_line.split("\t")
        if "FORMAT" in all_cols:
            fmt_idx = all_cols.index("FORMAT")
            sample_count = len(all_cols) - fmt_idx - 1
            summary["sample_count"] = sample_count
            if sample_count == 0:
                issues.append(ValidationIssue(
                    field="samples", message="No sample columns found", severity="warning",
                ))

    # Count data records
    for line in lines:
        if not line.startswith("#"):
            record_count += 1

    summary["variant_count"] = record_count

    if record_count == 0:
        issues.append(ValidationIssue(
            field="records", message="No variant records found", severity="warning",
        ))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.VCF, filename=path.name,
        valid=valid, issues=issues, record_count=record_count, summary=summary,
    )
