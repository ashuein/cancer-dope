"""RNA expression (counts / TPM) parser and validator."""

import csv
from pathlib import Path

from backend.models.inputs import InputValidationResult, ValidationIssue, InputType


def validate_expression(path: Path, input_type: InputType | None = None) -> InputValidationResult:
    """Validate a TSV/CSV expression file with gene_id, gene_name, and value columns."""
    if input_type is None:
        input_type = InputType.RNA_TPM

    issues: list[ValidationIssue] = []
    summary: dict = {}
    record_count = 0

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=input_type, filename=path.name, valid=False, issues=issues,
        )

    try:
        with open(path, "r") as f:
            # Detect delimiter
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
            reader = csv.DictReader(f, delimiter=dialect.delimiter)

            if reader.fieldnames is None:
                issues.append(ValidationIssue(
                    field="header", message="No header row found", severity="error",
                ))
                return InputValidationResult(
                    input_type=input_type, filename=path.name, valid=False, issues=issues,
                )

            headers = set(reader.fieldnames)
            summary["columns"] = list(reader.fieldnames)

            # Check required columns
            if "gene_id" not in headers and "gene_name" not in headers:
                issues.append(ValidationIssue(
                    field="columns",
                    message="Must have at least one of: gene_id, gene_name",
                    severity="error",
                ))

            # Check for a value column
            value_cols = headers - {"gene_id", "gene_name"}
            if not value_cols:
                issues.append(ValidationIssue(
                    field="columns", message="No value columns found", severity="error",
                ))
            summary["value_columns"] = sorted(value_cols)

            # Count and validate rows
            for row in reader:
                record_count += 1
                if record_count <= 5:
                    # Spot-check numeric values in first 5 rows
                    for col in value_cols:
                        val = row.get(col, "")
                        if val:
                            try:
                                float(val)
                            except ValueError:
                                issues.append(ValidationIssue(
                                    field=col,
                                    message=f"Non-numeric value at row {record_count}: {val}",
                                    severity="error",
                                ))

    except Exception as e:
        issues.append(ValidationIssue(field="file", message=f"Cannot parse file: {e}", severity="error"))
        return InputValidationResult(
            input_type=input_type, filename=path.name, valid=False, issues=issues,
        )

    summary["gene_count"] = record_count
    if record_count == 0:
        issues.append(ValidationIssue(field="records", message="No data rows found", severity="warning"))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=input_type, filename=path.name,
        valid=valid, issues=issues, record_count=record_count, summary=summary,
    )
