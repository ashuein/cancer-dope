# Architecture Diagrams — PrecisionOncology Portal

**Date:** April 1, 2026  
**Reference:** [architecture-assessment.md](architecture-assessment.md) | [osteosarc_webpage_analysis.md](osteosarc_webpage_analysis.md)

All diagrams use Unicode box-drawing characters for portability.

---

## 1. Runtime Service Map

```text
┌──────────────────────────────────────────────────────────────────────┐
│                            DOCKER COMPOSE                           │
├──────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐      ┌─────────────┐                                │
│  │    web      │─────▶│     api     │                                │
│  │ Vue 3 SPA   │ HTTP │ FastAPI     │                                │
│  │ TS + Vite   │ WS   │ REST + WS   │                                │
│  └─────────────┘      └─────┬───────┘                                │
│                              │                                        │
│               ┌──────────────┼───────────────────────┐                │
│               │              │                       │                │
│         ┌─────▼─────┐  ┌─────▼─────┐           ┌────▼─────┐          │
│         │ worker-   │  │ worker-   │           │ worker-   │          │
│         │ core      │  │ pvactools │           │ rnaseq    │          │
│         └─────┬─────┘  └─────┬─────┘           └────┬─────┘          │
│               │              │                       │                │
│         ┌─────▼─────┐  ┌─────▼─────┐           ┌────▼─────┐          │
│         │ worker-   │  │ worker-   │           │ worker-   │          │
│         │ scrna     │  │ r         │           │ cnv       │          │
│         └─────┬─────┘  └─────┬─────┘           └────┬─────┘          │
│               │              │                       │                │
│               └──────────────┼───────────────┬───────┘                │
│                              │               │                        │
│                        ┌─────▼─────┐   ┌────▼─────┐                   │
│                        │ worker-   │   │ sqlite   │                   │
│                        │ imaging   │   │ metadata │                   │
│                        └─────┬─────┘   └──────────┘                   │
│                              │                                        │
│                    ┌─────────▼─────────┐                              │
│                    │ artifact volume    │                              │
│                    │ reference volume   │                              │
│                    └────────────────────┘                              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Workflow and Provenance Model

```text
Case
 ├─ metadata
 ├─ inputs
 └─ AnalysisRun
     ├─ StepRun
     │   ├─ Artifact
     │   └─ ExternalCall
     ├─ StepRun
     │   ├─ Artifact
     │   └─ ExternalCall
     └─ VisualizationDataset
```

---

## 3. Input -> Module -> Artifact -> Page Flow

```text
RAW / IMPORTED INPUTS
════════════════════════════════════════════════════════════════════
Clinical tables    Genomics / RNA      Single-cell      Imaging
VCF / BAM / SEG    FASTQ / TPM         AnnData / Zarr   Tiles / Xenium
MRD / labs / flow  HLA / vaccine data  DE tables        Story manifests
        │                 │                 │                 │
        └────────────┬────┴──────────┬──────┴────────────┬────┘
                     ▼               ▼                   ▼
                  MODULES        MODULES             MODULES
              Clinical Timeline  Track1/Track2       Imaging/Spatial
              Bulk RNA           CNV / BAM           Data Catalog
              scRNA              GSEA
                     │               │                   │
                     └───────┬───────┴──────────┬────────┘
                             ▼                  ▼
                       REGISTERED ARTIFACTS   DERIVED DATASETS
                             │                  │
                             └──────────┬───────┘
                                        ▼
                                  FRONTEND PAGES
```

---

## 4. Page Dependency Map

```text
Timeline page
  <- clinical_timeline_json
  <- mrd_timeseries_json
  <- lab_timeseries_json
  <- flow_cytometry_json

Bulk RNA page
  <- bulk_rnaseq_matrix
  <- bulk_rnaseq_lookup_json
  <- bulk_reference_parquet

scRNA page
  <- scrnaseq_zarr
  <- scrnaseq metadata tables
  <- scrnaseq_de_parquet

GSEA page
  <- gsea_parquet
  <- DE tables
  <- expression-linked lookup datasets

CNV page
  <- cnv_seg
  <- cnv_bigwig
  <- CNV QC images

BAM page
  <- BAM / CRAM artifacts
  <- igv manifest
  <- named loci manifest

Vaccine page
  <- neoantigen_overlap_json
  <- VAF trend dataset

Imaging page
  <- image_tile_manifest
  <- story manifests

Spatial page
  <- spatial_bundle

Data page
  <- data_catalog_json

Track 1 page
  <- track1_results_json

Track 2 page
  <- track2_results_json
```

---

## 5. Delivery Roadmap

```text
Foundation
  ├─ Case / Run / Artifact model
  ├─ Storage layout
  ├─ Worker orchestration
  └─ Visualization dataset builders
        │
        ▼
Portal baseline
  ├─ Overview
  ├─ Timeline
  └─ Data catalog
        │
        ▼
Ranking modules
  ├─ Track 1 / vaccine overlap
  └─ Track 2
        │
        ▼
Browser modules
  ├─ CNV
  └─ BAM
        │
        ▼
Expression modules
  ├─ Bulk RNA
  ├─ scRNA
  └─ GSEA
        │
        ▼
Imaging / spatial
  ├─ Imaging gallery
  └─ Spatial viewer
```
