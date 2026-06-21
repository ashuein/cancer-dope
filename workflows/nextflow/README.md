# Nextflow smoke workflow

This folder contains a minimal Nextflow workflow skeleton for the cancer-dope project.
It is intentionally scoped to `workflows/nextflow/**` so it can evolve independently of
backend and application code.

## Inputs

Required parameters:

- `--case_manifest`: Path to a case manifest file. JSON, CSV, and TSV manifests are parsed
  with Python standard-library helpers when possible.
- `--outdir`: Directory where smoke artifacts are published. Defaults to `results`.

## Outputs

The smoke workflow publishes two artifact groups under `--outdir`:

- `manifest_artifact/<manifest-name>`: A validated copy of the input manifest.
- `data_catalog_json/catalog.json`: A small data catalog with the manifest name, detected
  format, record count, field names, up to five preview records, and parser warnings.

## Run

From this folder:

```bash
nextflow run main.nf --case_manifest path/to/case_manifest.csv --outdir results
```

Or from the repository root:

```bash
nextflow run workflows/nextflow/main.nf \
  -c workflows/nextflow/nextflow.config \
  --case_manifest path/to/case_manifest.csv \
  --outdir workflows/nextflow/results
```

The workflow fails fast when `--case_manifest` is omitted, does not exist, or is empty.
