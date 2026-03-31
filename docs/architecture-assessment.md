# Architecture Assessment --- PrecisionOncology Pipeline v1

**Date:** March 31, 2026
**Assessed against:** [precision-oncology-pipeline-plan-v1.md](precision-oncology-pipeline-plan-v1.md)

---

## 1. Strengths of the v1 Plan

| Strength | Detail |
|---|---|
| **Tool selection** | Every bioinformatics tool is established, peer-reviewed, and community-maintained |
| **Two-track architecture** | Neoantigen and drug-target tracks share input processing but remain independently runnable |
| **Explicit scoring formulas** | Both ranking functions are fully specified with weights --- no black-box scoring |
| **API-first for GPU tasks** | AlphaFold/ESMFold via API is the correct call given 4GB VRAM |
| **Realistic scoping** | No FASTQ processing, no scRNA core, no clinical claims --- appropriate for local compute |
| **Rate limit awareness** | AF3 20 jobs/day constraint explicitly handled with queue design |
| **Storage planning** | 752GB estimated on 8TB HDD with clear download/skip decisions |

---

## 2. Architecture Risks and Mitigations

### Risk 1: Python Version Conflict
**Problem:** pVACtools requires Python 3.8, FastAPI requires 3.10+. Cannot coexist in one environment.
**Impact:** Build-breaking. Pipeline cannot start if both are in the same venv.
**Mitigation:** Run pVACtools in an isolated Docker container (Python 3.8 base image). The FastAPI host process (Python 3.11) communicates with it via HTTP sidecar (see Section 4.3).
**Files affected:** `docker/pvactools.Dockerfile`, `engine/track1/neoantigen_engine.py`

### Risk 2: No Error Recovery or Checkpointing
**Problem:** Pipeline steps can run for hours (HLA typing, BLAST, AlphaFold queue). A failure at step 7 of 9 loses all prior work.
**Impact:** Wasted compute time. User frustration on re-runs.
**Mitigation:** Persist step-level state in SQLite via the `step_runs` table (see Section 3: Workflow Model). Each pipeline step writes its status and output artifacts to DB before proceeding. On restart, resume from the last successfully completed step. Output files are tracked as `artifacts` with SHA256 checksums for reproducibility.
**Files affected:** `db/models.py`, `engine/pipeline_runner.py`, `queue/job_queue.py`

### Risk 3: SQLite Concurrency Limitations
**Problem:** SQLite allows only one writer at a time. Concurrent pipeline runs or simultaneous AlphaFold queue updates could bottleneck.
**Impact:** Queue stalls under concurrent usage.
**Mitigation:** Enable WAL (Write-Ahead Logging) mode for concurrent reads + single writer. Use connection pooling with retry logic. For v1 (single-user local deployment), this is acceptable. Document PostgreSQL upgrade path for multi-user scenarios.
**Files affected:** `db/database.py`

### Risk 4: Polling-Based Progress Updates
**Problem:** v1 plan uses GET `/track1/status/{id}` and `/track2/status/{id}` for progress. Client must poll repeatedly.
**Impact:** Poor UX (delayed updates), wasted HTTP requests, no real-time feedback.
**Mitigation:** Add WebSocket endpoint `WS /ws/pipeline/{session_id}`. Backend pushes step transitions, progress percentages, and log lines in real-time. Keep REST status endpoints as fallback for non-WebSocket clients.
**Files affected:** `routers/ws.py`, frontend `stores/pipelineStore.ts`, `components/pipeline/StepProgress.vue`

### Risk 5: No Configuration Management
**Problem:** v1 plan does not mention how API URLs, rate limits, file paths, or feature flags are configured. Risk of hardcoded values scattered across modules.
**Impact:** Maintenance burden. Difficult deployment across environments.
**Mitigation:** Use `pydantic-settings` with a `.env` file. All external URLs, rate limits, directory paths, and feature toggles centralized in `config/settings.py`. Provide `.env.example` in the repository.
**Files affected:** `config/settings.py`, `.env.example`

### Risk 6: AlphaFold Rate Limit Fragility
**Problem:** AF3 server allows 20 jobs/day. The plan mentions queuing top-20 candidates, but doesn't handle day-boundary tracking, failed job retries, or partial-day usage.
**Impact:** Silent quota exhaustion. Jobs stuck in queue indefinitely.
**Mitigation:** Track submissions in SQLite with timestamps. Use rolling 24-hour window (not calendar day). Display remaining quota in UI. Auto-fallback to ColabFold when AF3 quota is exhausted. Retry failed jobs once before falling back.
**Files affected:** `queue/af_queue.py`, `engine/structure_engine.py`, frontend `components/pipeline/QueueStatus.vue`

### Risk 7: No Automated Test Strategy
**Problem:** v1 plan has per-phase "Validate" steps but no unit or integration test plan. No test data specification.
**Impact:** Regression risk as modules are added. No CI/CD readiness.
**Mitigation:** Add `tests/` directory with:
- `fixtures/` containing sample VCF (10 variants), RNA-seq TSV (100 genes), HLA report
- Unit tests for each parser and scoring function
- Integration tests for each engine module (with mocked external API responses)
- Frontend: Vitest + Vue Test Utils for component tests
**Files affected:** `tests/`, `tests/fixtures/`, frontend `tests/`

### Risk 8: No Service Health Checks
**Problem:** The pipeline depends on 10+ external tools and APIs. No way to verify they're all reachable before starting a run.
**Impact:** Confusing mid-pipeline failures. User uploads data, waits 30 minutes, then gets "NetMHCpan not found".
**Mitigation:** Add `/health` endpoint that checks:
- Each Docker container is running
- NetMHCpan binary is accessible
- Each external API is reachable (lightweight ping)
- Disk space sufficient
- GPU available (for DeepImmuno)
Display health dashboard in frontend before pipeline start.
**Files affected:** `routers/health.py`, frontend `components/shared/HealthCheck.vue`

### Risk 9: Docker Volume and File I/O Complexity
**Problem:** Bioinformatics tools in separate containers need access to shared input files, intermediate outputs, and cached structures. Volume mount configuration can be error-prone.
**Impact:** File-not-found errors between containers. Performance issues with large file I/O through Docker volumes on Windows.
**Mitigation:** Define a single shared Docker volume `pipeline-data` mounted at `/data` in all containers. Use subdirectories: `/data/uploads/`, `/data/intermediate/`, `/data/results/`, `/data/cache/`. Document volume structure in setup guide. Use bind mounts for development, named volumes for production.
**Files affected:** `docker-compose.yml`, all engine modules (path configuration)

### Risk 10: NetMHCpan Cannot Be Auto-Installed
**Problem:** NetMHCpan requires manual download with academic license acceptance. Cannot be bundled in Docker image or installed via package manager.
**Impact:** Onboarding friction. First-time setup requires manual steps that are easy to get wrong.
**Mitigation:** Document the installation clearly in setup guide with screenshots/links. Provide a verification script (`scripts/verify-netmhcpan.sh`) that confirms correct installation. Make NetMHCpan optional --- pipeline runs without it but warns that binding affinity step will be skipped.
**Files affected:** `docs/dependency-setup-guide.md`, `scripts/verify-netmhcpan.sh`, `engine/track1/binding_scorer.py`

---

## 3. Workflow Model

The v1 plan describes pipeline steps but lacks a first-class workflow/run model for reproducibility and audit. The following entities define the execution model explicitly:

### 3.1 Entity Definitions

| Entity | Purpose | Key Fields |
|---|---|---|
| **Session** | One user analysis. Created at upload time. | `id`, `created_at`, `status`, `input_files`, `config` |
| **AnalysisRun** | One execution of a session (supports re-runs). A session may have multiple runs if the user re-runs with different parameters or resumes after failure. | `id`, `session_id`, `run_number`, `started_at`, `completed_at`, `status`, `config_snapshot` |
| **StepRun** | One execution of a pipeline step within an analysis run. This is the checkpoint/resume unit. | `id`, `run_id`, `step_name`, `track`, `status`, `started_at`, `completed_at`, `input_artifact_ids`, `output_artifact_ids`, `error_message` |
| **Artifact** | A versioned file or data blob produced by a step. Inputs to downstream steps reference artifacts, not raw file paths. Enables provenance tracing: "which step produced this PDB?" | `id`, `step_run_id`, `artifact_type` (vcf, pdb, tsv, json), `file_path`, `sha256`, `created_at` |
| **ExternalCall** | A logged call to an external API or tool subprocess. Enables audit: "when was ESMFold called, with what input, what was the response?" | `id`, `step_run_id`, `service` (esmfold, af3, reactome, etc.), `request_summary`, `response_status`, `latency_ms`, `called_at` |

### 3.2 Provenance Chain

```
Session
  +-- AnalysisRun (run_number=1)
       +-- StepRun: variant_processing
       |     +-- Artifact: annotated_variants.json (output)
       |     +-- ExternalCall: Ensembl VEP (200 OK, 3200ms)
       +-- StepRun: hla_typing
       |     +-- Artifact: hla_alleles.json (output)
       +-- StepRun: binding_affinity
       |     +-- Artifact: binding_results.tsv (output)
       |     +-- ExternalCall: NetMHCpan subprocess (exit 0, 45000ms)
       +-- ...
```

This model replaces the simpler `pipeline_steps` table proposed earlier. The `pipeline_steps` table in Section 6 becomes `StepRun`. The key addition is `Artifact` (versioned outputs with checksums) and `ExternalCall` (audit log for API and subprocess calls). Together they provide full reproducibility: given the same session inputs, the pipeline should produce identical artifacts, and any divergence is traceable to a specific external call.

### 3.3 Implementation Note

For v1, `Artifact` and `ExternalCall` can be implemented as lightweight SQLite tables. They do not require a full workflow engine (Airflow, Prefect). The `pipeline_runner.py` orchestrator writes these records as it executes steps. If a future version needs formal workflow orchestration, the data model is compatible with migration to a workflow engine.

---

## 4. Docker Architecture Design

> In v1, FastAPI runs as a **host process**. Docker Compose manages only the bioinformatics tool containers. See Section 4.3 for the full rationale.

### 4.1 Container Topology

```
HOST PROCESS (not containerized):
  FastAPI (Python 3.11, uvicorn :8000)
    |
    +--- HTTP -------> pvactools container (:8001 sidecar)
    +--- docker compose run --rm ---> blast container
    +--- docker compose run --rm ---> fpocket container
    +--- docker compose run --rm ---> r-engine container
    |
    +--- reads/writes ---> ./data/ (shared bind-mount)

DOCKER CONTAINERS (tool isolation only):
  +--------------------+     +------------------+
  |  pvactools         |     |  blast           |
  |  Python 3.8        |     |  BLAST+ latest   |
  |  HTTP :8001        |     |  On-demand only  |
  |  Long-running      |     |                  |
  +--------------------+     +------------------+

  +--------------------+     +------------------+
  |  fpocket           |     |  r-engine        |
  |  Ubuntu 22.04      |     |  R 4.3 + dNdScv  |
  |  On-demand only    |     |  On-demand only  |
  +--------------------+     +------------------+

Shared Data Directory (host bind-mount into all containers):
  ./data/uploads/        Input files (VCF, RNA-seq, HLA)
  ./data/intermediate/   Step outputs (annotated VCF, peptide lists, etc.)
  ./data/results/        Final ranked tables, scores
  ./data/cache/          PDB structure cache
  ./data/blast-db/       Human proteome BLAST database
```

### 4.2 Container Specifications

| Service | Base Image | Purpose | Communication |
|---|---|---|---|
| `pvactools` | `python:3.8-slim` | pVACtools neoantigen generation | HTTP :8001 sidecar, long-running |
| `blast` | `ncbi/blast:latest` | BLAST+ cross-reactivity search | `docker compose run --rm` from host |
| `fpocket` | `ubuntu:22.04` + build | fpocket pocket detection | `docker compose run --rm` from host |
| `r-engine` | `r-base:4.3` | dNdScv driver gene analysis | `docker compose run --rm` from host |

### 4.3 Communication Patterns

#### Where orchestration runs in v1

**The FastAPI backend runs as a host process, not inside a container.** Docker Compose manages only the bioinformatics tool containers. FastAPI runs directly on the host via `uvicorn`. This means:

- The host process has direct access to the Docker Compose CLI (no socket mount needed).
- Subprocess calls to `docker compose run --rm blast ...` work naturally from the host.
- The shared data directory is a host bind-mount accessible to both the host process and tool containers.
- SQLite database lives on the host filesystem, avoiding Docker volume performance issues on Windows.

If a future version needs to containerize FastAPI itself (e.g., for cloud deployment), the communication pattern must switch to HTTP sidecars for all tools, or accept the Docker socket tradeoff documented below.

#### Communication options considered

**Option A (rejected): `docker exec` from a containerized app**
- Would require mounting the Docker socket (`/var/run/docker.sock`) into the app container.
- Security risk: a vulnerability in FastAPI could escalate to full Docker host control.
- Not needed in v1 since FastAPI runs on the host.

**Option B: HTTP Sidecar**
- Tool container runs a thin Flask/FastAPI wrapper.
- Host process calls `http://localhost:port/run` with JSON payload.
- Better isolation, but more setup per tool.
- **Used for pVACtools** (complex I/O, long-running).

**Option C: Shared Volume + `docker compose run`** (recommended for CLI tools)
- Host process writes input files to `./data/intermediate/`.
- Host process runs `docker compose run --rm blast blastp ...`.
- Tool container reads input, writes output to the same bind-mounted directory.
- No Docker socket mount, no HTTP overhead.
- **Used for BLAST, fpocket, R** (simple CLI tools).

- The FastAPI process has direct access to the Docker Compose CLI (no socket mount needed).
- Subprocess calls to `docker compose run --rm blast ...` work naturally from the host.
- The shared data directory is a host bind-mount accessible to both the host process and tool containers.
- SQLite database lives on the host filesystem, avoiding Docker volume performance issues on Windows.

If a future version needs to containerize the FastAPI app itself (e.g., for cloud deployment), the communication pattern must switch to either HTTP sidecars for all tools, or accept the Docker socket mount tradeoff.

**v1 Recommendation:**
- **pVACtools:** HTTP sidecar (complex I/O, already planned). The pVACtools container runs a thin Flask API; FastAPI calls it via HTTP.
- **BLAST, fpocket, R:** Option C (shared volume + `docker compose run`). FastAPI (on host) writes inputs to the shared data directory, then shells out to `docker compose run --rm blast blastp ...`. Tool containers read input, write output to the same directory.
- **If Option C proves impractical** (e.g., `docker compose` CLI unavailable or too slow for repeated calls), fall back to Docker socket mount with a clear warning in the setup guide and a `DOCKER_SOCKET_MOUNT=true` flag in `.env`.

---

## 5. User-Friendliness Improvements

### 5.1 Input Experience
| Improvement | Description |
|---|---|
| **Guided wizard** | Step-by-step upload: (1) VCF file (2) RNA-seq file (3) HLA config --- with validation at each step |
| **Format auto-detection** | Detect VCF version, column count in RNA-seq, HLA format automatically |
| **Error messages** | Map common failures to fixes: "VCF has no CHROM column" -> "This appears to be a BED file, not VCF. Expected columns: CHROM, POS, ID, REF, ALT..." |
| **Demo mode** | One-click pipeline run with bundled sample data subset. No file upload needed. |

### 5.2 Pipeline Monitoring
| Improvement | Description |
|---|---|
| **Real-time progress** | WebSocket-driven step transitions with progress bar per step |
| **Time estimates** | ETA per step based on input size (variant count -> neoantigen time, gene count -> pathway mapping time) |
| **Step explanations** | Expandable "What does this step do?" panel in plain English for each pipeline step |
| **Log viewer** | Scrollable real-time log output filterable by step. Useful for debugging. |
| **Browser persistence** | Refresh browser without losing progress --- state lives in backend, frontend reconnects via WebSocket |

### 5.3 Results Experience
| Improvement | Description |
|---|---|
| **Keyboard navigation** | Arrow keys + Enter to navigate results table, Escape to go back |
| **Side-by-side comparison** | Select two candidates and compare their evidence panels |
| **HTML export** | Self-contained HTML report (embeds charts as SVG) in addition to PDF/JSON |
| **Score breakdown** | Click any final score to see the weighted component breakdown |
| **Risk explanations** | Hover on risk flags to see plain-English explanation of what the flag means |

### 5.4 General UX
| Improvement | Description |
|---|---|
| **Loading skeletons** | Skeleton UI while data loads, not blank screens |
| **Empty states** | Helpful empty states ("No results yet --- start a pipeline run") |
| **Error boundaries** | Graceful error display with retry buttons, not white screens |
| **Responsive layout** | Usable on tablet-width screens (1024px+) |

---

## 6. Recommended Architecture Changes vs v1 Plan

| Change | v1 Plan | Recommended |
|---|---|---|
| Environment | WSL2 assumed | Docker Compose (with WSL2-backed Docker Desktop on Windows). Docker and WSL2 are not mutually exclusive: Docker Desktop on Windows uses WSL2 as its backend. The recommendation is to use Docker Compose as the primary orchestration layer, which happens to run on WSL2 on Windows. |
| Frontend language | JavaScript (.js) | TypeScript (.ts) |
| Progress updates | REST polling | WebSocket push + REST fallback |
| Configuration | Not specified | pydantic-settings + .env |
| Error recovery | Not specified | Per-step checkpointing in SQLite |
| Engine structure | Flat `engine/` | Split `engine/track1/`, `engine/track2/` |
| Health checks | Not specified | `/health` endpoint + UI dashboard |
| Testing | Manual validation | pytest + vitest automated tests |
| pVACtools isolation | "isolated venv" | Isolated Docker container |
| New endpoints | --- | `/health`, `/version`, `WS /ws/pipeline/{id}` |
| New modules | --- | `config/settings.py`, `routers/ws.py`, `routers/health.py`, `middleware/error_handler.py` |
| New frontend | --- | `HealthCheck.vue`, WebSocket store, loading skeletons, error boundaries |

---

## 7. Data Model Additions

The v1 plan defines `NeoantigenCandidate` and `DrugTargetCandidate`. The following tables implement the workflow model from Section 3. The earlier `pipeline_steps` concept is superseded by `step_runs` + `artifacts` + `external_calls`.

### analysis_runs
```
id             UUID    PK
session_id     UUID    FK -> sessions
run_number     INTEGER Auto-increment per session (supports re-runs)
status         TEXT    "pending" | "running" | "completed" | "failed"
started_at     TEXT    ISO timestamp
completed_at   TEXT    ISO timestamp (nullable)
config_snapshot TEXT   JSON snapshot of settings used for this run
```

### step_runs
```
id             UUID    PK
run_id         UUID    FK -> analysis_runs
step_name      TEXT    e.g. "hla_typing", "binding_affinity"
track          TEXT    "track1" | "track2" | "shared"
step_order     INTEGER Execution order within the track
status         TEXT    "pending" | "running" | "completed" | "failed"
started_at     TEXT    ISO timestamp
completed_at   TEXT    ISO timestamp (nullable)
error_message  TEXT    Error detail if failed (nullable)
```

### artifacts
```
id             UUID    PK
step_run_id    UUID    FK -> step_runs
artifact_type  TEXT    "vcf" | "pdb" | "tsv" | "json"
file_path      TEXT    Path relative to /data/
sha256         TEXT    Checksum for integrity/reproducibility
created_at     TEXT    ISO timestamp
```

### external_calls
```
id             UUID    PK
step_run_id    UUID    FK -> step_runs
service        TEXT    "esmfold" | "af3" | "colabfold" | "reactome" | "chembl" | "netmhcpan" | etc.
request_summary TEXT   Brief description of what was sent
response_status TEXT   HTTP status or exit code
latency_ms     INTEGER
called_at      TEXT    ISO timestamp
```

### alphafold_jobs (expanded from plan)
```
id             UUID    PK
session_id     UUID    FK -> sessions
candidate_id   UUID    FK -> track1_candidates or track2_candidates
candidate_type TEXT    "neoantigen" | "drug_target"
service        TEXT    "af3" | "esmfold" | "colabfold"
status         TEXT    "queued" | "submitted" | "running" | "completed" | "failed"
submitted_at   TEXT    ISO timestamp
completed_at   TEXT    ISO timestamp (nullable)
pdb_path       TEXT    Local cache path to PDB file (nullable)
plddt_score    REAL    Confidence score (nullable)
retry_count    INTEGER Default 0
error_message  TEXT    (nullable)
```

### structure_cache
```
sequence_hash  TEXT    PK (SHA256 of input sequence)
service        TEXT    "af3" | "esmfold" | "colabfold"
pdb_path       TEXT    Local file path
plddt_score    REAL    (nullable)
created_at     TEXT    ISO timestamp
```
