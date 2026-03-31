# Architecture Diagrams --- PrecisionOncology Pipeline

**Date:** March 31, 2026
**Reference:** [architecture-assessment.md](architecture-assessment.md) | [precision-oncology-pipeline-plan-v1.md](precision-oncology-pipeline-plan-v1.md)

All diagrams use Unicode box-drawing characters for portability.

---

## 1. System Deployment Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          HOST MACHINE                                   │
│                    Windows 11 / Linux / macOS                           │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  HOST PROCESSES (native, not containerized)                       │  │
│  │                                                                    │  │
│  │  ┌───────────────────────────┐  ┌──────────────────────────────┐  │  │
│  │  │  FastAPI Backend          │  │  Frontend Dev Server         │  │  │
│  │  │  Python 3.11 + uvicorn    │  │  Node.js 20 LTS + Vite      │  │  │
│  │  │  Port :8000               │  │  Port :5173                  │  │  │
│  │  │  WebSocket support        │  │  Vue 3 + TypeScript          │  │  │
│  │  │  Orchestrates pipeline    │  │  Pinia + Vue Router          │  │  │
│  │  │  Calls docker compose run │  │  ECharts + 3Dmol.js          │  │  │
│  │  └─────────┬─────────────────┘  └──────────────────────────────┘  │  │
│  │            │                                                       │  │
│  │            │ HTTP to :8001 (pvactools sidecar)                     │  │
│  │            │ docker compose run (blast, fpocket, r-engine)         │  │
│  │            │ Reads/writes shared data directory                    │  │
│  └────────────┼──────────────────────────────────────────────────────┘  │
│               │                                                         │
│               ▼                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  DOCKER ENGINE (tool containers only)                           │   │
│  │                                                                  │   │
│  │  ┌───────────────────────┐  ┌───────────────────────┐           │   │
│  │  │  pvactools            │  │  blast                │           │   │
│  │  │  Python 3.8           │  │  BLAST+ latest        │           │   │
│  │  │  Sidecar HTTP :8001   │  │  docker compose run   │           │   │
│  │  └───────────────────────┘  └───────────────────────┘           │   │
│  │                                                                  │   │
│  │  ┌───────────────────────┐  ┌───────────────────────┐           │   │
│  │  │  fpocket              │  │  r-engine             │           │   │
│  │  │  Ubuntu 22.04         │  │  R 4.3 + dNdScv       │           │   │
│  │  │  docker compose run   │  │  docker compose run   │           │   │
│  │  └───────────────────────┘  └───────────────────────┘           │   │
│  │                                                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  SHARED DATA DIRECTORY (host bind-mount into all containers)     │   │
│  │  ./data/uploads/        Input files (VCF, RNA-seq, HLA)          │   │
│  │  ./data/intermediate/   Step outputs (annotated VCF, peptides)   │   │
│  │  ./data/results/        Final ranked tables, scores              │   │
│  │  ./data/cache/          PDB structure file cache                 │   │
│  │  ./data/blast-db/       Human proteome BLAST database            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  LOCAL RESOURCES                                                 │   │
│  │  SQLite DB: ./backend/pipeline.db                                │   │
│  │  NetMHCpan 4.1: /opt/netMHCpan-4.1/ (manual install)           │   │
│  │  GTX 1650 GPU: DeepImmuno (4GB VRAM, marginal)                  │   │
│  │  8TB HDD: Structure cache, genomic data storage                  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       EXTERNAL APIs                                     │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ AlphaFold3   │  │ ESMFold      │  │ ColabFold    │                  │
│  │ Server       │  │ HuggingFace  │  │ API          │                  │
│  │ 20 jobs/day  │  │ Free tier    │  │ Rate-limited │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ Reactome     │  │ ChEMBL       │  │ DGIdb        │                  │
│  │ REST API     │  │ REST API     │  │ REST API     │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ pkCSM        │  │ GTEx         │  │ Ensembl VEP  │                  │
│  │ REST API     │  │ REST API     │  │ REST API     │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pipeline Data Flow

```
                          ┌─────────────────────┐
                          │     USER UPLOADS     │
                          │  VCF + RNA-seq TSV   │
                          │  + HLA (BAM or TXT)  │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │  INPUT VALIDATION    │
                          │  Format check        │
                          │  Column validation   │
                          │  Session creation     │
                          └──────────┬──────────┘
                                     │
                          ┌──────────▼──────────┐
                          │ VARIANT PROCESSOR    │
                          │ VCF parse (cyvcf2)   │
                          │ VEP annotation (API) │
                          │ Somatic filtering     │
                          │ Mutation classifying   │
                          └─────┬──────────┬─────┘
                                │          │
               ┌────────────────┘          └────────────────┐
               │                                            │
    ┌──────────▼──────────┐                     ┌───────────▼─────────┐
    │     TRACK 1          │                     │      TRACK 2        │
    │  NEOANTIGEN          │                     │   DRUG TARGET       │
    │                      │                     │                     │
    │  Step 1: HLA Typing  │                     │  Step 1: Driver     │
    │    OptiType (Docker)  │                     │    Genes            │
    │    or pre-typed input │                     │    dNdScv (Docker)  │
    │         │            │                     │         │           │
    │  Step 2: Neoantigen  │                     │  Step 2: Mutant     │
    │    Generation        │                     │    Protein Struct   │
    │    pVACtools (Docker) │                     │    ESMFold (API)    │
    │         │            │                     │         │           │
    │  Step 3: Binding     │                     │  Step 3: Pocket     │
    │    Affinity          │                     │    Detection        │
    │    NetMHCpan (local)  │                     │    fpocket (Docker) │
    │         │            │                     │         │           │
    │  Step 4: Structure   │                     │  Step 4: Pathway    │
    │    Validation        │                     │    Mapping          │
    │    AlphaFold3 (API)  │                     │    Reactome (API)   │
    │    ColabFold fallback │                     │         │           │
    │         │            │                     │  Step 5: Drug       │
    │  Step 5: Exposure    │                     │    Matching         │
    │    Analysis          │                     │    ChEMBL + DGIdb   │
    │    BioPython SASA     │                     │         │           │
    │         │            │                     │  Step 6: Toxicity   │
    │  Step 6: Expression  │                     │    Pre-filter       │
    │    Filter            │                     │    pkCSM (API)      │
    │    Pandas TPM check   │                     │         │           │
    │         │            │                     │  Step 7: Normal     │
    │  Step 7: Immuno-     │                     │    Tissue Check     │
    │    genicity          │                     │    GTEx (API)       │
    │    DeepImmuno (GPU)  │                     │         │           │
    │    IEDB fallback      │                     │  Step 8: Track 2   │
    │         │            │                     │    Ranking          │
    │  Step 8: Cross-      │                     │    Scoring formula  │
    │    Reactivity        │                     │                     │
    │    BLAST (Docker)     │                     └───────────┬─────────┘
    │    ESMFold compare    │                                 │
    │         │            │                                 │
    │  Step 9: Track 1     │                                 │
    │    Ranking           │                                 │
    │    Scoring formula   │                                 │
    │                      │                                 │
    └──────────┬───────────┘                                 │
               │                                             │
               └─────────────────┬───────────────────────────┘
                                 │
                      ┌──────────▼──────────┐
                      │   UNIFIED RANKER    │
                      │   Merge + sort      │
                      │   Evidence tagging  │
                      │   Risk flag overlay │
                      └──────────┬──────────┘
                                 │
                      ┌──────────▼──────────┐
                      │   RESULTS OUTPUT    │
                      │   Ranked table      │
                      │   Candidate detail  │
                      │   Structure viewer  │
                      │   PDF / JSON / HTML │
                      └─────────────────────┘
```

---

## 3. Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (Vue 3 + TS)                    │
│                                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ InputView  │ │ Pipeline-  │ │ Track1/2   │ │ Candidate-   │ │
│  │            │ │ View       │ │ View       │ │ DetailView   │ │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └──────┬───────┘ │
│        │              │              │               │          │
│  ┌─────▼──────────────▼──────────────▼───────────────▼───────┐  │
│  │                    PINIA STORES                            │  │
│  │  sessionStore | pipelineStore | track1Store | track2Store  │  │
│  │  structureStore | resultStore                             │  │
│  └─────────────────────────┬─────────────────────────────────┘  │
│                             │                                    │
│  ┌──────────────────────────▼────────────────────────────────┐  │
│  │                    API CLIENT LAYER                        │  │
│  │  inputApi | track1Api | track2Api | alphaFoldApi           │  │
│  │  resultApi | wsClient (WebSocket)                         │  │
│  └──────────────────────────┬────────────────────────────────┘  │
└─────────────────────────────┼────────────────────────────────────┘
                              │ HTTP / WebSocket
                              │
┌─────────────────────────────▼────────────────────────────────────┐
│                        BACKEND (FastAPI)                          │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                      ROUTERS                               │   │
│  │  input.py | track1.py | track2.py | alphafold.py           │   │
│  │  results.py | ws.py | health.py                           │   │
│  └───────────┬───────────────────────────────┬───────────────┘   │
│              │                               │                    │
│  ┌───────────▼───────────┐    ┌──────────────▼────────────────┐  │
│  │     MIDDLEWARE         │    │         CONFIG                │  │
│  │  error_handler.py      │    │  settings.py (pydantic)      │  │
│  │  request_logger.py     │    │  .env file                   │  │
│  └───────────┬───────────┘    └───────────────────────────────┘  │
│              │                                                    │
│  ┌───────────▼───────────────────────────────────────────────┐   │
│  │                    ENGINE LAYER                            │   │
│  │                                                            │   │
│  │  ┌─── track1/ ───────────────┐  ┌─── track2/ ──────────┐ │   │
│  │  │ hla_typer.py              │  │ driver_gene_engine.py │ │   │
│  │  │ neoantigen_engine.py      │  │ pocket_engine.py      │ │   │
│  │  │ binding_scorer.py         │  │ pathway_engine.py     │ │   │
│  │  │ expression_filter.py      │  │ drug_matcher.py       │ │   │
│  │  │ immunogenicity_scorer.py  │  │ toxicity_engine.py    │ │   │
│  │  │ cross_reactivity_engine.py│  │ gtex_engine.py        │ │   │
│  │  │ track1_ranker.py          │  │ track2_ranker.py      │ │   │
│  │  └───────────────────────────┘  └───────────────────────┘ │   │
│  │                                                            │   │
│  │  ┌─── shared/ ───────────────────────────────────────────┐│   │
│  │  │ variant_processor.py | structure_engine.py            ││   │
│  │  │ pipeline_runner.py   | report_engine.py               ││   │
│  │  └───────────────────────────────────────────────────────┘│   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │   PARSERS      │  │   DB LAYER    │  │   QUEUE + CACHE      │  │
│  │ vcf_parser     │  │ database.py   │  │ job_queue.py         │  │
│  │ rnaseq_parser  │  │ session_repo  │  │ af_queue.py          │  │
│  │ hla_parser     │  │ result_repo   │  │ structure_cache.py   │  │
│  │ pdb_parser     │  │ queue_repo    │  │                      │  │
│  └───────────────┘  └───────┬───────┘  └──────────────────────┘  │
│                              │                                    │
└──────────────────────────────┼────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  SQLite Database    │
                    │  WAL mode enabled   │
                    │  pipeline.db        │
                    └─────────────────────┘
```

---

## 4. Database Schema

```
┌──────────────────────────────────────────────────────────────────┐
│                        DATABASE SCHEMA                            │
│                     SQLite (WAL mode)                             │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────────────┐
│       sessions          │
├─────────────────────────┤
│ id          UUID   PK   │
│ created_at  TEXT        │
│ status      TEXT        │──── "created" | "validating" | "running"
│ vcf_path    TEXT        │     | "completed" | "failed"
│ rnaseq_path TEXT        │
│ hla_source  TEXT        │──── "optitype" | "pretyped"
│ hla_alleles TEXT (JSON) │
│ tracks      TEXT (JSON) │──── ["track1"] | ["track2"] | ["track1","track2"]
│ config      TEXT (JSON) │──── runtime parameters
└──────────┬──────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────────┐
│    analysis_runs        │
├─────────────────────────┤
│ id          UUID   PK   │
│ session_id  UUID   FK ──│──┐
│ run_number  INTEGER     │  │
│ status      TEXT        │  │
│ started_at  TEXT        │  │
│ completed_at TEXT       │  │
│ config_snapshot TEXT    │  │
└──────────┬──────────────┘  │
           │ 1:N             │
           ▼                 │
┌─────────────────────────┐  │   ┌─────────────────────────────────┐
│    step_runs            │  │   │      track1_candidates          │
├─────────────────────────┤  │   ├─────────────────────────────────┤
│ id          UUID   PK   │  │   │ id                UUID   PK     │
│ run_id      UUID   FK   │  │   │ session_id        UUID   FK ────│──┐
│ step_name   TEXT        │  │   │ peptide_sequence  TEXT          │  │
│ track       TEXT        │  │   │ source_gene       TEXT          │  │
│ step_order  INTEGER     │  │   │ mutation          TEXT          │  │
│ status      TEXT        │  │   │ mutation_type     TEXT          │  │
│ started_at  TEXT        │  │   │ hla_allele        TEXT          │  │
│ completed_at TEXT       │  │   │ ic50_nm           REAL          │  │
│ error_msg   TEXT        │  │   │ percentile_rank   REAL          │  │
└──────────┬──────────────┘  │   │ af3_plddt         REAL          │  │
           │ 1:N             │   │ sasa_exposed_pct  REAL          │  │
           ▼                 │   │ tpm_expression    REAL          │  │
┌─────────────────────────┐  │   │ immunogenicity    REAL          │  │
│    artifacts            │  │   │ cross_react_risk  REAL          │  │
├─────────────────────────┤  │
│ id          UUID   PK   │  │
│ step_run_id UUID   FK   │  │
│ artifact_type TEXT      │  │
│ file_path   TEXT        │  │
│ sha256      TEXT        │  │
│ created_at  TEXT        │  │
└─────────────────────────┘  │
                             │
┌─────────────────────────┐  │
│    external_calls       │  │
├─────────────────────────┤  │
│ id          UUID   PK   │  │
│ step_run_id UUID   FK   │  │
│ service     TEXT        │  │
│ request_summary TEXT    │  │
│ response_status TEXT    │  │
│ latency_ms  INTEGER     │  │
│ called_at   TEXT        │  │
└─────────────────────────┘  │
                             │
           ┌─────────────────┘   │ cross_react_flag  TEXT          │  │
           │                     │ cross_react_flag  TEXT          │  │
           │                     │ final_score       REAL          │  │
           │                     │ risk_flags        TEXT (JSON)   │  │
           │                     └─────────────────────────────────┘  │
           │                                                          │
           │                     ┌─────────────────────────────────┐  │
           │                     │      track2_candidates          │  │
           │                     ├─────────────────────────────────┤  │
           │                     │ id                UUID   PK     │  │
           ├─────────────────────│ session_id        UUID   FK ────│──┤
           │                     │ gene              TEXT          │  │
           │                     │ mutation          TEXT          │  │
           │                     │ dndscv_qvalue     REAL          │  │
           │                     │ druggability      REAL          │  │
           │                     │ pocket_volume     REAL          │  │
           │                     │ drug_name         TEXT          │  │
           │                     │ drug_smiles       TEXT          │  │
           │                     │ mechanism         TEXT          │  │
           │                     │ evidence_level    TEXT          │  │
           │                     │ pathway           TEXT          │  │
           │                     │ toxicity_flags    TEXT (JSON)   │  │
           │                     │ normal_tissue_risk TEXT         │  │
           │                     │ gtex_max_tissue   TEXT          │  │
           │                     │ final_score       REAL          │  │
           │                     │ risk_flags        TEXT (JSON)   │  │
           │                     └─────────────────────────────────┘  │
           │                                                          │
           │                     ┌─────────────────────────────────┐  │
           │                     │      alphafold_jobs             │  │
           │                     ├─────────────────────────────────┤  │
           │                     │ id              UUID   PK       │  │
           ├─────────────────────│ session_id      UUID   FK ──────│──┘
                                 │ candidate_id    UUID            │
                                 │ candidate_type  TEXT            │
                                 │ service         TEXT            │
                                 │ status          TEXT            │
                                 │ submitted_at    TEXT            │
                                 │ completed_at    TEXT            │
                                 │ pdb_path        TEXT            │
                                 │ plddt_score     REAL            │
                                 │ retry_count     INTEGER         │
                                 │ error_msg       TEXT            │
                                 └─────────────────────────────────┘

┌─────────────────────────────────┐     ┌──────────────────────────────┐
│      structure_cache            │     │       job_queue               │
├─────────────────────────────────┤     ├──────────────────────────────┤
│ sequence_hash  TEXT   PK        │     │ id            UUID   PK      │
│ service        TEXT             │     │ session_id    UUID   FK      │
│ pdb_path       TEXT             │     │ job_type      TEXT           │
│ plddt_score    REAL             │     │ status        TEXT           │
│ created_at     TEXT             │     │ priority      INTEGER        │
│                                 │     │ created_at    TEXT           │
│                                 │     │ started_at    TEXT           │
│                                 │     │ completed_at  TEXT           │
│                                 │     │ error_msg     TEXT           │
└─────────────────────────────────┘     └──────────────────────────────┘
```

---

## 5. Docker Service Map

> In v1, FastAPI runs as a **host process** (not containerized). Docker Compose
> manages only the bioinformatics tool containers. The host process calls
> `docker compose run` for CLI tools and HTTP for the pVACtools sidecar.

```
HOST PROCESS (not in Docker):
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI (uvicorn) on host                                          │
│  - Reads/writes ./data/ directly                                    │
│  - Calls http://localhost:8001 for pVACtools                        │
│  - Calls `docker compose run --rm blast ...` for BLAST              │
│  - Calls `docker compose run --rm fpocket ...` for fpocket          │
│  - Calls `docker compose run --rm r-engine ...` for dNdScv          │
│  - SQLite DB at ./backend/pipeline.db (host filesystem)             │
└─────────────────────────────────────────────────────────────────────┘

DOCKER COMPOSE (tool containers only):
┌─────────────────────────────────────────────────────────────────────┐
│                      docker-compose.yml                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  SERVICE: pvactools                                          │    │
│  │  Image: cancer-drug/pvactools:latest                        │    │
│  │  Build: docker/pvactools.Dockerfile                          │    │
│  │  Ports: 8001:8001 (exposed to host)                          │    │
│  │  Volumes:                                                    │    │
│  │    - ./data:/data                                            │    │
│  │  Note: Python 3.8, HTTP sidecar. Long-running service.       │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  SERVICE: blast                                              │    │
│  │  Image: ncbi/blast:latest                                   │    │
│  │  Volumes:                                                    │    │
│  │    - ./data:/data                                            │    │
│  │  Note: Invoked via `docker compose run --rm`. Not always on. │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  SERVICE: fpocket                                            │    │
│  │  Image: cancer-drug/fpocket:latest                          │    │
│  │  Build: docker/fpocket.Dockerfile                            │    │
│  │  Volumes:                                                    │    │
│  │    - ./data:/data                                            │    │
│  │  Note: Invoked via `docker compose run --rm`. Not always on. │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  SERVICE: r-engine                                           │    │
│  │  Image: cancer-drug/r-engine:latest                         │    │
│  │  Build: docker/r-engine.Dockerfile                           │    │
│  │  Volumes:                                                    │    │
│  │    - ./data:/data                                            │    │
│  │  Note: Invoked via `docker compose run --rm`. Not always on. │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. API Route Map

```
FastAPI Application (:8000)
│
├── /input/
│   ├── POST  /upload          Upload VCF + RNA-seq + HLA
│   ├── POST  /validate        Validate uploaded files
│   └── POST  /run             Start pipeline execution
│
├── /track1/
│   ├── GET   /status/{id}     Pipeline step progress
│   ├── GET   /results/{id}    Ranked neoantigen table
│   └── GET   /candidate/{id}  Full candidate detail
│
├── /track2/
│   ├── GET   /status/{id}     Pipeline step progress
│   ├── GET   /results/{id}    Ranked drug-target table
│   └── GET   /candidate/{id}  Full candidate detail
│
├── /alphafold/
│   ├── GET   /queue           Queue positions + ETAs
│   └── GET   /job/{id}        Job status + PDB download
│
├── /results/
│   ├── GET   /unified/{id}    Combined ranked output
│   └── GET   /export/{id}     PDF/JSON/HTML report
│
├── /health                    Service health check
├── /version                   API version info
│
└── /ws/
    └── WS    /pipeline/{id}   Real-time progress stream
```
