# Data Contracts

**Status:** Planning baseline for implementation. These contracts describe intended schemas and ownership boundaries; they do not imply current backend support.

---

## 1. Contract Principles

- The API is the source of truth for metadata and provenance.
- Nextflow is the selected workflow manager for analysis execution.
- Workflow processes should communicate outputs through manifest files.
- Frontend pages should consume page-ready visualization datasets, not raw workflow internals.
- Every user-visible value should be traceable to a registered artifact unless it is static application copy.
- Contracts should be versioned so old runs remain interpretable after schema changes.

---

## 2. Core Entity Contracts

### Case

```json
{
  "id": "case_001",
  "label": "Demo Case 001",
  "created_at": "2026-04-01T00:00:00Z",
  "metadata": {
    "diagnosis": "example diagnosis",
    "species": "human"
  }
}
```

Required fields:

- `id`
- `label`
- `created_at`
- `metadata`

### AnalysisRun

```json
{
  "id": "run_001",
  "case_id": "case_001",
  "status": "running",
  "module_selection": ["clinical_timeline", "bulk_rna"],
  "config_snapshot": {},
  "started_at": "2026-04-01T00:00:00Z",
  "completed_at": null
}
```

Allowed statuses:

- `queued`
- `running`
- `completed`
- `failed`
- `canceled`
- `completed_with_warnings`

### StepRun

```json
{
  "id": "step_001",
  "run_id": "run_001",
  "module": "clinical_timeline",
  "step_name": "import_clinical_events",
  "status": "completed",
  "started_at": "2026-04-01T00:01:00Z",
  "completed_at": "2026-04-01T00:02:00Z",
  "error_message": null,
  "warnings": []
}
```

Allowed statuses:

- `queued`
- `running`
- `completed`
- `failed`
- `skipped`
- `canceled`
- `completed_with_warnings`

### Artifact

```json
{
  "id": "artifact_001",
  "step_run_id": "step_001",
  "artifact_type": "clinical_timeline_json",
  "format": "json",
  "path": "data/cases/case_001/runs/run_001/artifacts/timeline.json",
  "checksum": "sha256:example",
  "status": "available",
  "created_at": "2026-04-01T00:02:00Z"
}
```

Allowed statuses:

- `available`
- `pending`
- `failed_validation`
- `superseded`
- `deleted`

### VisualizationDataset

```json
{
  "id": "viz_001",
  "case_id": "case_001",
  "run_id": "run_001",
  "page": "timeline",
  "schema_version": "1.0.0",
  "source_artifact_ids": ["artifact_001"],
  "path": "data/cases/case_001/runs/run_001/derived/frontend/timeline.dataset.json",
  "created_at": "2026-04-01T00:03:00Z"
}
```

Required fields:

- `id`
- `case_id`
- `run_id`
- `page`
- `schema_version`
- `source_artifact_ids`
- `path`
- `created_at`

---

## 3. Input Manifest Contract

The input manifest describes files and structured inputs available to a run.

```json
{
  "schema_version": "1.0.0",
  "case_id": "case_001",
  "created_at": "2026-04-01T00:00:00Z",
  "inputs": [
    {
      "input_id": "input_001",
      "input_type": "clinical_events_table",
      "format": "csv",
      "path": "data/cases/case_001/inputs/clinical_events.csv",
      "checksum": "sha256:example",
      "metadata": {
        "date_column": "event_date"
      }
    }
  ]
}
```

Rules:

- Each input must declare `input_type`, `format`, `path`, and `checksum` when available.
- Paths should be case-scoped and should not point outside approved input or reference roots.
- Input manifests should be immutable for a run once execution begins.

---

## 4. Workflow Handoff Contract

The API should hand Nextflow a run-level package rather than granting workflow code direct metadata ownership.

```json
{
  "schema_version": "1.0.0",
  "case_id": "case_001",
  "run_id": "run_001",
  "module_selection": ["clinical_timeline", "bulk_rna"],
  "input_manifest_path": "data/cases/case_001/inputs/input-manifest.json",
  "output_root": "data/cases/case_001/runs/run_001/artifacts",
  "derived_root": "data/cases/case_001/runs/run_001/derived/frontend",
  "reference_root": "data/reference",
  "config_snapshot_path": "data/cases/case_001/runs/run_001/config.json"
}
```

Rules:

- `run_id` must be unique and immutable.
- `output_root` and `derived_root` must be run-scoped.
- `module_selection` controls which Nextflow modules are eligible to execute.
- The handoff package should be preserved as part of run provenance.

---

## 5. Module Output Manifest Contract

Each module should emit an output manifest for API ingestion.

```json
{
  "schema_version": "1.0.0",
  "case_id": "case_001",
  "run_id": "run_001",
  "module": "clinical_timeline",
  "step_name": "build_timeline_dataset",
  "status": "completed",
  "artifacts": [
    {
      "artifact_type": "clinical_timeline_json",
      "format": "json",
      "path": "data/cases/case_001/runs/run_001/artifacts/timeline.json",
      "checksum": "sha256:example"
    }
  ],
  "visualization_datasets": [
    {
      "page": "timeline",
      "schema_version": "1.0.0",
      "path": "data/cases/case_001/runs/run_001/derived/frontend/timeline.dataset.json",
      "source_artifact_paths": [
        "data/cases/case_001/runs/run_001/artifacts/timeline.json"
      ]
    }
  ],
  "warnings": []
}
```

Rules:

- A manifest may contain artifacts, visualization datasets, or both.
- Paths must be under the run-scoped output or derived roots.
- The API should compute or verify checksums before marking artifacts available.
- Failed steps should still emit enough structured information to update `StepRun` status when possible.

---

## 6. Artifact Type Baseline

| Artifact type | Format | Primary page or consumer |
|---|---|---|
| `clinical_timeline_json` | JSON | Timeline |
| `mrd_timeseries_json` | JSON | Timeline |
| `lab_timeseries_json` | JSON | Timeline |
| `flow_cytometry_json` | JSON | Timeline |
| `bulk_rnaseq_matrix` | Parquet/Zarr/CSV | Bulk RNA |
| `bulk_rnaseq_lookup_json` | JSON | Bulk RNA |
| `bulk_reference_parquet` | Parquet | Bulk RNA |
| `scrnaseq_zarr` | Zarr | scRNA |
| `scrnaseq_de_parquet` | Parquet | scRNA, GSEA |
| `gsea_parquet` | Parquet | GSEA |
| `cnv_seg` | SEG/TSV | CNV |
| `cnv_bigwig` | BigWig | CNV, genome browser |
| `bam` | BAM | BAM browser |
| `bai` | BAI | BAM browser |
| `neoantigen_overlap_json` | JSON | Vaccine overlap, Track 1 |
| `spatial_bundle` | Directory/Zarr/JSON | Spatial |
| `image_tile_manifest` | JSON | Imaging |
| `data_catalog_json` | JSON | Data catalog |
| `track1_results_json` | JSON | Track 1 |
| `track2_results_json` | JSON | Track 2 |

---

## 7. Visualization Dataset Contracts

### Common envelope

Every page-ready dataset should use a common envelope:

```json
{
  "schema_version": "1.0.0",
  "case_id": "case_001",
  "run_id": "run_001",
  "page": "timeline",
  "generated_at": "2026-04-01T00:03:00Z",
  "source_artifact_ids": ["artifact_001"],
  "data": {}
}
```

### Timeline page dataset

Expected `data` fields:

- `events`
- `tracks`
- `mrd_series`
- `lab_series`
- `flow_series`
- `display_config`

### Bulk RNA page dataset

Expected `data` fields:

- `gene_index`
- `sample_index`
- `expression_matrix_ref`
- `comparison_tables`
- `display_config`

### scRNA page dataset

Expected `data` fields:

- `embedding_ref`
- `cell_metadata_ref`
- `cluster_summary`
- `gene_overlay_ref`
- `differential_expression_tables`

### GSEA page dataset

Expected `data` fields:

- `pathway_summary`
- `heatmap_matrix`
- `volcano_points`
- `linked_expression_refs`

### CNV and BAM page datasets

Expected `data` fields:

- `igv_manifest`
- `loci`
- `tracks`
- `qc_artifacts`

### Imaging and spatial page datasets

Expected `data` fields:

- `tile_manifest`
- `spatial_manifest`
- `regions_of_interest`
- `display_config`

### Catalog page dataset

Expected `data` fields:

- `artifacts`
- `runs`
- `modules`
- `download_groups`

---

## 8. API Response Shape Baseline

Visualization endpoint responses should distinguish unavailable modules from empty datasets.

```json
{
  "case_id": "case_001",
  "page": "timeline",
  "status": "available",
  "dataset": {},
  "provenance": {
    "run_id": "run_001",
    "source_artifact_ids": ["artifact_001"]
  },
  "message": null
}
```

Allowed visualization response statuses:

- `available`
- `not_requested`
- `pending`
- `failed`
- `empty`
- `missing_required_inputs`

---

## 9. Versioning Expectations

- `schema_version` should be present on manifests and page-ready datasets.
- Breaking schema changes should increment the major version.
- The API should preserve enough metadata to route old datasets to compatible readers or migration code.
- Documentation should list supported schema versions once implementation starts.
