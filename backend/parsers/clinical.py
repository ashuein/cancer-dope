"""Clinical timeline CSV and JSON validators.

Clinical data has a fundamentally different schema from expression data:
it contains event/date columns, not gene/value columns.
"""

import csv
import json
from pathlib import Path

from backend.models.inputs import InputType, InputValidationResult, ValidationIssue

# At least one date-like column expected
_DATE_COLUMN_HINTS = {"date", "start_date", "end_date", "event_date", "timestamp",
                       "diagnosis_date", "treatment_start", "treatment_end", "collection_date"}

# At least one event/type column expected
_EVENT_COLUMN_HINTS = {"event_type", "type", "category", "event", "treatment",
                        "procedure", "modality", "test_name", "assay"}


def validate_clinical_csv(path: Path) -> InputValidationResult:
    """Validate a clinical timeline CSV file."""
    issues: list[ValidationIssue] = []
    summary: dict = {}
    record_count = 0

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.CLINICAL_CSV, filename=path.name, valid=False, issues=issues,
        )

    try:
        with open(path, "r") as f:
            sample = f.read(4096)
            f.seek(0)
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
            reader = csv.DictReader(f, delimiter=dialect.delimiter)

            if reader.fieldnames is None:
                issues.append(ValidationIssue(
                    field="header", message="No header row found", severity="error",
                ))
                return InputValidationResult(
                    input_type=InputType.CLINICAL_CSV, filename=path.name, valid=False, issues=issues,
                )

            headers_lower = {h.lower().strip() for h in reader.fieldnames}
            summary["columns"] = list(reader.fieldnames)

            # Check for date columns
            date_cols = headers_lower & _DATE_COLUMN_HINTS
            if not date_cols:
                issues.append(ValidationIssue(
                    field="columns",
                    message=f"No date column found. Expected one of: {', '.join(sorted(_DATE_COLUMN_HINTS))}",
                    severity="warning",
                ))
            else:
                summary["date_columns"] = sorted(date_cols)

            # Check for event/type columns
            event_cols = headers_lower & _EVENT_COLUMN_HINTS
            if not event_cols:
                issues.append(ValidationIssue(
                    field="columns",
                    message=f"No event/type column found. Expected one of: {', '.join(sorted(_EVENT_COLUMN_HINTS))}",
                    severity="warning",
                ))
            else:
                summary["event_columns"] = sorted(event_cols)

            for row in reader:
                record_count += 1

    except Exception as e:
        issues.append(ValidationIssue(field="file", message=f"Cannot parse file: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.CLINICAL_CSV, filename=path.name, valid=False, issues=issues,
        )

    summary["record_count"] = record_count
    if record_count == 0:
        issues.append(ValidationIssue(field="records", message="No data rows found", severity="warning"))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.CLINICAL_CSV, filename=path.name,
        valid=valid, issues=issues, record_count=record_count, summary=summary,
    )


def validate_clinical_json(path: Path) -> InputValidationResult:
    """Validate a clinical timeline JSON file."""
    issues: list[ValidationIssue] = []
    summary: dict = {}

    if not path.is_file():
        issues.append(ValidationIssue(field="path", message="File not found", severity="error"))
        return InputValidationResult(
            input_type=InputType.CLINICAL_JSON, filename=path.name, valid=False, issues=issues,
        )

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        issues.append(ValidationIssue(field="file", message=f"Invalid JSON: {e}", severity="error"))
        return InputValidationResult(
            input_type=InputType.CLINICAL_JSON, filename=path.name, valid=False, issues=issues,
        )

    if isinstance(data, list):
        summary["record_count"] = len(data)
        summary["type"] = "array"
        # Check first record for expected fields
        if data:
            first = data[0]
            if isinstance(first, dict):
                keys_lower = {k.lower() for k in first.keys()}
                date_found = bool(keys_lower & _DATE_COLUMN_HINTS)
                event_found = bool(keys_lower & _EVENT_COLUMN_HINTS)
                if not date_found:
                    issues.append(ValidationIssue(
                        field="structure", message="No date field found in first record", severity="warning",
                    ))
                if not event_found:
                    issues.append(ValidationIssue(
                        field="structure", message="No event/type field found in first record", severity="warning",
                    ))
                summary["sample_keys"] = list(first.keys())
    elif isinstance(data, dict):
        summary["top_level_keys"] = list(data.keys())
        summary["type"] = "object"
        # Could be a manifest with nested events
        for key in ("events", "treatments", "timeline", "records"):
            if key in data and isinstance(data[key], list):
                summary["record_count"] = len(data[key])
                break
    else:
        issues.append(ValidationIssue(
            field="root", message="Expected a JSON object or array", severity="error",
        ))

    valid = not any(i.severity == "error" for i in issues)
    return InputValidationResult(
        input_type=InputType.CLINICAL_JSON, filename=path.name,
        valid=valid, issues=issues, summary=summary,
    )
