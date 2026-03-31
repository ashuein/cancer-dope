# PrecisionOncology Pipeline

> **Status: Planning stage.** The repository currently contains design documents only. The architecture, commands, endpoints, and task list below describe the intended implementation, not the current repo state.

An open-source, Dockerized oncology analysis pipeline and portal that accepts raw or processed patient datasets, produces versioned analysis artifacts, and serves osteosarc-style visualization pages from those artifacts.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Vue 3](https://img.shields.io/badge/Vue-3-brightgreen.svg)](https://vuejs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://typescriptlang.org)
[![Research Grade](https://img.shields.io/badge/Output-Research%20Grade-orange.svg)](#disclaimer)

> **Research grade output only. Not for clinical use.**

---

## What It Targets

The documented target is no longer just a two-track ranking app. The repo is planned as a **case-based analysis platform** with:

- Dockerized analysis modules
- case and run management
- artifact registration and provenance
- derived visualization datasets
- a multi-page portal for longitudinal, omics, structure, genome-browser, and imaging outputs

The design is anchored to the output classes documented in [docs/osteosarc_webpage_analysis.md](docs/osteosarc_webpage_analysis.md). The goal is **functional equivalence** to those output surfaces using open-source, containerized tooling, not a pixel-identical clone of `osteosarc.com`.

---

## Product Shape

### Core Platform
- Case-based data organization
- Checkpointed analysis runs with resumable steps
- Versioned artifacts with provenance
- Derived frontend datasets for page rendering
- Downloadable catalog of generated outputs

### Analysis Modules
- Clinical timeline and longitudinal lab module
- Neoantigen and vaccine overlap module
- Drug-target ranking module
- Bulk RNA expression module
- scRNA module
- GSEA module
- CNV and genome track module
- BAM browser module
- Imaging and spatial module

### Planned Visualization Pages
- Overview / case home
- Timeline
- Bulk RNA
- scRNA
- GSEA
- CNV
- BAM browser
- Vaccine overlap
- Imaging
- Spatial
- Data catalog
- Track 1 neoantigen ranking
- Track 2 drug-target ranking

---

## Supported Input Modes

### Raw Mode
- FASTQ / BAM / CRAM for genomics and transcriptomics
- clinical event tables
- lab and MRD time-series
- flow cytometry series
- slide images and spatial outputs

### Processed Import Mode
- VCF
- TPM or count matrices
- AnnData / Zarr
- Parquet result tables
- SEG / BigWig
- BAM / BAI
- Xenium-compatible bundles
- JSON exports and static manifests

Processed import is the preferred first delivery path for the heaviest modules.

---

## Architecture Overview

```text
Browser (Vue 3 + TypeScript)
    |
    v
FastAPI API container
    |
    +---> Case / Run / Artifact APIs
    +---> Visualization dataset APIs
    +---> WebSocket run events
    |
    +---> Worker containers
    |       +-- worker-core
    |       +-- worker-pvactools
    |       +-- worker-rnaseq
    |       +-- worker-scrna
    |       +-- worker-r
    |       +-- worker-cnv
    |       +-- worker-imaging
    |
    +---> SQLite metadata DB
    +---> Artifact volume on disk
    +---> Reference-data volume on disk
```

Track 1 and Track 2 remain in scope, but they are now modules within a broader analysis and visualization system.

---

## Primary Artifact Formats

- JSON for longitudinal and page-ready datasets
- Parquet for tabular analytical outputs
- Zarr for large matrix-style expression datasets
- BAM / BAI or CRAM / CRAI for genome browsing
- SEG and BigWig for copy-number and track visualization
- tiled image bundles for pathology viewing
- manifest files for CNV, BAM, imaging, and spatial pages

---

## Planned API Surface

| Method | Endpoint | Description |
|---|---|---|
| POST | `/cases` | Create a case |
| GET | `/cases/{case_id}` | Get case summary and module availability |
| POST | `/cases/{case_id}/inputs` | Upload or register inputs |
| POST | `/cases/{case_id}/runs` | Start an analysis run |
| GET | `/cases/{case_id}/runs/{run_id}` | Get run summary |
| GET | `/cases/{case_id}/runs/{run_id}/steps` | Step-by-step execution state |
| GET | `/cases/{case_id}/artifacts` | List artifacts for a case |
| GET | `/artifacts/{artifact_id}/download` | Download one artifact |
| GET | `/visualizations/{case_id}/{page}` | Return page-ready dataset payload |
| GET | `/tracks/{case_id}/igv-manifest` | Genome-browser manifest for CNV/BAM pages |
| GET | `/catalog/{case_id}` | Data catalog view model |
| GET | `/health` | Service and dependency health |
| WS | `/runs/{run_id}/events` | Real-time run events |

---

## Planned Frontend Routes

- `/`
- `/cases/:caseId`
- `/cases/:caseId/timeline`
- `/cases/:caseId/rnaseq`
- `/cases/:caseId/scrna`
- `/cases/:caseId/gsea`
- `/cases/:caseId/cnv`
- `/cases/:caseId/bams`
- `/cases/:caseId/vaccines`
- `/cases/:caseId/imaging`
- `/cases/:caseId/spatial`
- `/cases/:caseId/data`
- `/cases/:caseId/track1`
- `/cases/:caseId/track2`

---

## Planned Runtime and Storage Model

### Core entities
- `Case`
- `AnalysisRun`
- `StepRun`
- `Artifact`
- `VisualizationDataset`
- `ExternalCall`

### Planned storage layout
```text
data/
  cases/{case_id}/inputs/
  cases/{case_id}/runs/{run_id}/artifacts/
  cases/{case_id}/runs/{run_id}/derived/frontend/
  reference/
```

SQLite is planned for metadata and provenance. Large files remain on disk as registered artifacts.

---

## Documentation

- [Architecture Assessment](docs/architecture-assessment.md) - Canonical architecture direction
- [Architecture Diagrams](docs/architecture-diagram.md) - Runtime, workflow, and page-dependency diagrams
- [Dependency Setup Guide](docs/dependency-setup-guide.md) - Planned container and dependency design
- [Task List](docs/task-list.md) - Granular implementation checklist
- [Osteosarc Webpage Analysis](docs/osteosarc_webpage_analysis.md) - Output/visualization anchor document
- [Project Plan v1](docs/precision-oncology-pipeline-plan-v1.md) - Historical baseline

---

## License

This project is licensed under the **GNU Affero General Public License v3.0**. See [LICENSE](LICENSE) for details.

Third-party tools may impose separate license terms. Users are responsible for complying with those terms independently.

---

## Disclaimer

This repository is intended for research, engineering, and reproducibility work only. It is not a medical device, not a clinical decision support system, and not a source of treatment recommendations.
