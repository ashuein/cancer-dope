nextflow.enable.dsl = 2

params.case_manifest = params.case_manifest ?: null
params.outdir = params.outdir ?: 'results'

workflow {
    if (!params.case_manifest) {
        error "Missing required parameter: --case_manifest <path>"
    }

    manifest_ch = channel.fromPath(params.case_manifest, checkIfExists: true)

    SMOKE_CASE_MANIFEST(manifest_ch)
}

process SMOKE_CASE_MANIFEST {
    tag { manifest.simpleName }

    publishDir params.outdir, mode: 'copy'

    input:
    path manifest

    output:
    path 'manifest_artifact/*', emit: manifest_artifact
    path 'data_catalog_json/catalog.json', emit: data_catalog_json

    script:
    """
    set -euo pipefail

    MANIFEST='${manifest}'
    MANIFEST_BASENAME='${manifest.name}'

    if [ ! -s "\$MANIFEST" ]; then
        echo "Manifest is missing or empty: \$MANIFEST" >&2
        exit 1
    fi

    mkdir -p manifest_artifact data_catalog_json
    cp "\$MANIFEST" "manifest_artifact/\$MANIFEST_BASENAME"

    python3 - "\$MANIFEST" "\$MANIFEST_BASENAME" <<'PY'
import csv
import json
import pathlib
import sys
from typing import Any

manifest_path = pathlib.Path(sys.argv[1])
manifest_name = sys.argv[2]
raw_text = manifest_path.read_text(encoding="utf-8-sig")

warnings: list[str] = []
records: list[dict[str, Any]] = []
fields: list[str] = []
manifest_format = "text"

try:
    parsed = json.loads(raw_text)
except json.JSONDecodeError:
    parsed = None

if parsed is not None:
    manifest_format = "json"
    if isinstance(parsed, list):
        records = [item for item in parsed if isinstance(item, dict)]
        if len(records) != len(parsed):
            warnings.append("JSON list contains non-object entries that were omitted from preview records.")
    elif isinstance(parsed, dict):
        candidate_rows = None
        for key in ("cases", "samples", "records", "items"):
            if isinstance(parsed.get(key), list):
                candidate_rows = parsed[key]
                break
        if candidate_rows is not None:
            records = [item for item in candidate_rows if isinstance(item, dict)]
            if len(records) != len(candidate_rows):
                warnings.append("Nested JSON list contains non-object entries that were omitted from preview records.")
        else:
            records = [parsed]
else:
    sample = raw_text[:4096]
    delimiter = "\t" if "\t" in sample else ","
    manifest_format = "tsv" if delimiter == "\t" else "csv"
    try:
        reader = csv.DictReader(raw_text.splitlines(), delimiter=delimiter)
        fields = list(reader.fieldnames or [])
        records = [dict(row) for row in reader]
    except csv.Error as exc:
        warnings.append(f"Could not parse manifest as delimited text: {exc}")
        manifest_format = "text"
        records = []

if not fields and records:
    seen: list[str] = []
    for record in records:
        for key in record.keys():
            if key not in seen:
                seen.append(key)
    fields = seen

catalog = {
    "manifest_name": manifest_name,
    "manifest_format": manifest_format,
    "record_count": len(records),
    "fields": fields,
    "preview_records": records[:5],
    "warnings": warnings,
}

catalog_path = pathlib.Path("data_catalog_json/catalog.json")
catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + chr(10), encoding="utf-8")
PY
    """
}
