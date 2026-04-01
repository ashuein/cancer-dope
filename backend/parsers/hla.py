"""HLA typing data parser and validator."""

import json
import re
from pathlib import Path

from backend.models.inputs import InputValidationResult, ValidationIssue, InputType

_HLA_ALLELE_RE = re.compile(r"^[A-Z]+\*\d{2,4}:\d{2,4}")


def validate_hla(path: Path) -> InputValidationResult:
    """Validate an HLA JSON file."""
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.HLA, filename=path.name, valid=False, issues=issues,
        )

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        issues.append(ValidationIssue(field="file", message=f"Invalid JSON: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.HLA, filename=path.name, valid=False, issues=issues,
        )

    if not isinstance(data, dict):
        issues.append(ValidationIssue(field="root", message="Expected a JSON object", severity="error"))
        return InputValidationResult(
            input_type=InputType.HLA, filename=path.name, valid=False, issues=issues,
        )

    # Check for class_i
    class_i = data.get("class_i", {})
    if not class_i:
        issues.append(ValidationIssue(
            field="class_i", message="Missing or empty class_i HLA typing", severity="warning",
        ))
    else:
        allele_count = 0
        for locus, alleles in class_i.items():
            if not isinstance(alleles, list):
                issues.append(ValidationIssue(
                    field=f"class_i.{locus}", message="Alleles must be a list", severity="error",
                ))
                continue
            for allele in alleles:
                if not _HLA_ALLELE_RE.match(allele):
                    issues.append(ValidationIssue(
                        field=f"class_i.{locus}",
                        message=f"Invalid allele format: {allele}",
                        severity="error",
                    ))
                allele_count += 1
        summary["class_i_alleles"] = allele_count

    # Check class_ii (optional)
    class_ii = data.get("class_ii", {})
    if class_ii:
        allele_count = 0
        for locus, alleles in class_ii.items():
            if isinstance(alleles, list):
                allele_count += len(alleles)
        summary["class_ii_alleles"] = allele_count

    summary["source"] = data.get("source", "unknown")

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.HLA, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )
