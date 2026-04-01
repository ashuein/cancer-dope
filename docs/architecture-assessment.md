# Architecture Assessment — PrecisionOncology Portal

**Date:** April 1, 2026  
**Primary references:** [osteosarc_webpage_analysis.md](osteosarc_webpage_analysis.md) | [precision-oncology-pipeline-plan-v1.md](precision-oncology-pipeline-plan-v1.md)

---

## 1. Purpose and Target Product

The current documented target is a **modular oncology analysis platform plus visualization portal**, not just a two-track ranking app.

The system should:
- ingest raw or processed patient data,
- run Dockerized, open-source analysis modules,
- emit versioned artifacts with provenance,
- derive page-ready visualization datasets from those artifacts,
- serve a multi-page portal that is functionally equivalent to the output classes described in the osteosarc reference analysis.

`osteosarc.com` is therefore an **output and visualization anchor**, not the implementation architecture to copy literally.

---

## 2. Scope Expansion from the Original v1 Plan

The historical v1 plan focused on two major tracks:
- Track 1: neoantigen ranking
- Track 2: drug-target ranking

Those remain in scope, but they are now only part of the broader platform. Newly in-scope modules are:

| Module | Purpose | Main outputs |
|---|---|---|
| Clinical Timeline | Longitudinal treatment, imaging, MRD, labs, flow | Timeline JSON and chart datasets |
| Bulk RNA | Expression exploration and reference comparison | Matrices, lookup tables, comparison datasets |
| scRNA | Embedding, metadata, cluster and gene exploration | Zarr, DE tables, embedding datasets |
| GSEA | Pathway enrichment and DE-linked views | fgsea parquet, heatmap and pathway datasets |
| CNV | Copy-number segments and browser tracks | SEG, BigWig, QC images, manifests |
| BAM Browser | Genomic read inspection | track manifests, named loci |
| Vaccine Overlap | Mutation-to-vaccine overlap and VAF trends | overlap JSON, VAF trend JSON |
| Imaging / Spatial | Pathology and Xenium-like viewing | tiled image bundles, spatial manifests |
| Data Catalog | Downloadable inventory of case outputs | artifact inventory dataset |

---

## 3. Canonical Workflow and Provenance Model

### 3.1 Core entities

| Entity | Purpose | Key fields |
|---|---|---|
| `Case` | Patient/project container | `id`, `label`, `created_at`, `metadata` |
| `AnalysisRun` | One execution over a case | `id`, `case_id`, `status`, `config_snapshot`, `started_at`, `completed_at` |
| `StepRun` | Checkpointable unit of execution | `id`, `run_id`, `module`, `step_name`, `status`, `started_at`, `completed_at`, `error_message` |
| `Artifact` | Versioned output file or dataset | `id`, `step_run_id`, `artifact_type`, `format`, `path`, `checksum`, `status`, `created_at` |
| `VisualizationDataset` | Frontend-ready bundle derived from artifacts | `id`, `case_id`, `page`, `source_artifact_ids`, `path`, `created_at` |
| `ExternalCall` | Audit log of public API or subprocess usage | `id`, `step_run_id`, `service`, `request_summary`, `response_status`, `latency_ms`, `called_at` |

### 3.2 Provenance rule

Every user-facing page must resolve back to:

`Case -> AnalysisRun -> StepRun -> Artifact -> VisualizationDataset`

### 3.3 Artifact taxonomy

Minimum artifact types:
- `clinical_timeline_json`
- `mrd_timeseries_json`
- `lab_timeseries_json`
- `flow_cytometry_json`
- `bulk_rnaseq_matrix`
- `bulk_rnaseq_lookup_json`
- `bulk_reference_parquet`
- `scrnaseq_zarr`
- `scrnaseq_de_parquet`
- `gsea_parquet`
- `cnv_seg`
- `cnv_bigwig`
- `bam`
- `neoantigen_overlap_json`
- `spatial_bundle`
- `image_tile_manifest`
- `data_catalog_json`
- `track1_results_json`
- `track2_results_json`

---

## 4. Module Architecture

### 4.1 Clinical Timeline Module
- Inputs: treatment history, procedures, imaging events, pathology dates, MRD, labs, flow cytometry
- Artifacts: timeline JSON, MRD JSON, lab JSON, flow JSON
- Visualization datasets: timeline rows and longitudinal panels
- Worker ownership: `worker-core`

### 4.2 Bulk RNA Module
- Inputs: raw FASTQ or processed count/TPM tables
- Artifacts: expression matrix, gene metadata table, comparison parquet/json
- Visualization datasets: gene explorer, assay comparison, CN-expression overlay
- Worker ownership: `worker-rnaseq`

### 4.3 scRNA Module
- Inputs: raw 10x outputs or processed AnnData/Zarr imports
- Artifacts: Zarr store, metadata tables, DE tables, cluster summaries
- Visualization datasets: embeddings, metadata facets, gene overlays, DE tables
- Worker ownership: `worker-scrna`

### 4.4 GSEA Module
- Inputs: DE tables from scRNA and optionally bulk RNA
- Artifacts: fgsea parquet, pathway summaries, volcano tables
- Visualization datasets: summary heatmap, pathway detail, volcano
- Worker ownership: `worker-r`

### 4.5 CNV Module
- Inputs: BAM-based pipelines or processed segments and signals
- Artifacts: SEG, BigWig, QC images, genome manifests
- Visualization datasets: CNV page dataset and IGV manifest
- Worker ownership: `worker-cnv`

### 4.6 BAM Browser Module
- Inputs: BAM / BAI or CRAM / CRAI
- Artifacts: track manifests, locus manifest
- Visualization datasets: browser configuration payload
- Worker ownership: `worker-core`

### 4.7 Neoantigen and Vaccine Module
- Inputs: variants, HLA, expression, vaccine design outputs, VAFs, optional ELISPOT
- Artifacts: candidate tables, overlap matrix JSON, VAF trend JSON, structures
- Visualization datasets: ranking tables, candidate detail datasets, overlap charts
- Worker ownership: `worker-pvactools` plus shared workers

### 4.8 Drug-Target Module
- Inputs: variants, optional copy number, pathway and drug lookups, structure and toxicity outputs
- Artifacts: driver tables, structure outputs, pathway summaries, drug match summaries
- Visualization datasets: ranking tables, candidate detail datasets, pathway views
- Worker ownership: `worker-core` and `worker-r`

### 4.9 Imaging and Spatial Module
- Inputs: image files, tiled assets, Xenium-compatible outputs, manifest files
- Artifacts: image tiles, story manifests, spatial manifests
- Visualization datasets: imaging gallery dataset and spatial viewer dataset
- Worker ownership: `worker-imaging`

### 4.10 Data Catalog Module
- Inputs: registered artifacts and source metadata
- Artifacts: catalog JSON
- Visualization datasets: searchable inventory model
- Worker ownership: `worker-core`

---

## 5. Runtime Architecture

The documentation uses one canonical runtime model:

- `web` container: frontend
- `api` container: FastAPI API and WebSocket layer
- worker containers per major module/toolchain
- SQLite metadata on mounted volume
- shared artifact and reference-data volumes

### 5.1 Service map

| Service | Role |
|---|---|
| `web` | Frontend SPA |
| `api` | Case/run/artifact API, visualization dataset API, WebSocket events |
| `worker-core` | Shared orchestration and import pipelines |
| `worker-pvactools` | pVACtools and neoantigen-specific path |
| `worker-rnaseq` | Bulk RNA compute and derived datasets |
| `worker-scrna` | Single-cell processing and exports |
| `worker-r` | R-driven DE/GSEA/CNV helpers |
| `worker-cnv` | CNV and genome-track generation |
| `worker-imaging` | Image tiling and viewer manifests |

### 5.2 Execution boundary

The API should:
- validate inputs,
- create runs,
- schedule steps,
- expose status and datasets.

Workers should:
- execute steps,
- write artifacts,
- register outputs and logs.

### 5.3 Storage design

```text
data/
  cases/{case_id}/inputs/
  cases/{case_id}/runs/{run_id}/artifacts/
  cases/{case_id}/runs/{run_id}/derived/frontend/
  reference/
```

Large files remain on disk. SQLite stores metadata and provenance only.

---

## 6. Visualization Architecture

| Page | Required datasets |
|---|---|
| Overview | case summary, run summary, module availability |
| Timeline | timeline rows, MRD series, lab panels, flow panels |
| Bulk RNA | gene explorer dataset, reference comparisons, assay comparison |
| scRNA | embedding dataset, metadata facets, gene overlays, DE table |
| GSEA | enrichment table, heatmap dataset, pathway detail dataset, volcano dataset |
| CNV | segment datasets, signal tracks, QC images |
| BAM Browser | IGV manifest, named loci |
| Vaccine Overlap | overlap matrix dataset, VAF trend dataset |
| Imaging | image gallery and story manifests |
| Spatial | spatial bundle and viewer configuration |
| Data Catalog | artifact inventory and download metadata |
| Track 1 | neoantigen table, filters, candidate detail |
| Track 2 | drug-target table, filters, candidate detail |

Every page contract must support partial-case behavior. Missing modules should produce an explicit “artifact not available” state, not a broken page.

---

## 7. Open-Source Tooling Direction

| Output surface | Recommended tooling |
|---|---|
| Timeline, overlap, scatter, heatmap | D3 and/or ECharts |
| BAM and CNV browsing | IGV.js |
| Tiled pathology | OpenSeadragon |
| scRNA and spatial viewing | Zarr-backed viewer or Vitessce-like approach |
| Browser-side parquet querying | DuckDB-WASM only where justified |

Parity target:
- same analysis class,
- same major interactions,
- same required output files and derived datasets,
- not identical code, layout, or exact frontend libraries.

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Scope expansion beyond original v1 | Delivery slippage | Deliver by module and page, not all at once |
| Large file sizes | Slow local setup | Support processed import mode and selective reference downloads |
| Browser performance for scRNA/spatial | Poor UX | Precompute datasets and avoid naive full-table browser loads |
| Artifact sprawl | Unclear outputs | Typed artifact registry and catalog module |
| Public API instability | Non-reproducible runs | Cache, log, and degrade gracefully |
| Imaging and spatial complexity | Viewer mismatch | Treat imaging/spatial as import-first modules |
| Partial data availability | Broken pages | Explicit capability flags and missing-artifact states |
| SQLite scalability | Multi-run contention | Accept for v1, document PostgreSQL upgrade path |

---

## 9. Recommended Delivery Order

1. Platform foundation
2. Overview, timeline, and data catalog
3. Track 1, vaccine overlap, and Track 2
4. CNV and BAM browser
5. Bulk RNA
6. scRNA and GSEA
7. Imaging and spatial

---

## 10. Recommended Changes vs the Historical v1 Plan

| Area | Historical v1 | Recommended current direction |
|---|---|---|
| Product framing | Two-track ranking app | Modular analysis portal with artifact-backed pages |
| Primary persistence concept | Session | Case + AnalysisRun + StepRun + Artifact |
| Inputs | Mostly VCF + RNA expression + HLA | Raw and processed multimodal inputs |
| Outputs | Ranked results and reports | Registered artifacts plus page-ready datasets |
| Frontend scope | Input, pipeline, track views, candidate detail | Multi-page portal plus ranking views |
| Runtime model | Narrow host/tool split | Consistent containerized API + workers |
| Storage | Results plus cache | Full artifact registry and case/run storage layout |

This document is the canonical architecture direction for the repository.
