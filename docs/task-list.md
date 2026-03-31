# Implementation Task List --- PrecisionOncology Pipeline

**Date:** March 31, 2026
**Total Tasks:** ~185
**Complexity Key:** `[S]` Small (< 1 hr) | `[M]` Medium (1-4 hrs) | `[L]` Large (4-8 hrs) | `[XL]` Extra Large (1-2 days)

---

## Critical Path

```
Phase 0 ──> Phase 1 ──> Phase 2 ──> Phase 3 ──> Phase 4 (Track 1 complete)
                   |
                   +──> Phase 5 (Track 2, can parallel Phase 3-4)

Phase 6 depends on Phase 2 + Phase 5 API contracts
Phase 7 depends on Phase 6
Phase 8 depends on Phase 6 + Phase 7
```

---

## Phase 0: Project Scaffolding

### 0.1 Repository Setup
- [ ] `[S]` Initialize git repository (`git init`)
- [ ] `[S]` Create directory structure: `backend/`, `frontend/`, `docker/`, `scripts/`, `tests/`, `data/`
- [ ] `[S]` Create `.env.example` with all environment variables
- [ ] `[S]` Create `docker-compose.yml` with all 5 services defined
- [ ] `[S]` Create `docker/app.Dockerfile` for FastAPI container
- [ ] `[S]` Create `docker/pvactools.Dockerfile` for pVACtools isolated container
- [ ] `[S]` Create `docker/fpocket.Dockerfile` for fpocket container
- [ ] `[S]` Create `docker/r-engine.Dockerfile` for R + dNdScv container
- [ ] `[M]` Verify all Docker containers build and start successfully

### 0.2 Backend Skeleton
- [ ] `[S]` Create `backend/requirements.txt` with all Python dependencies
- [ ] `[S]` Create `backend/main.py` --- FastAPI app init, CORS config, router mount
- [ ] `[S]` Create `backend/config/settings.py` --- pydantic-settings with all env vars
- [ ] `[S]` Create `backend/config/__init__.py`
- [ ] `[M]` Create `backend/db/database.py` --- SQLite connection with WAL mode, async engine
- [ ] `[M]` Create `backend/db/models.py` --- SQLAlchemy models for all tables (sessions, pipeline_steps, track1_candidates, track2_candidates, alphafold_jobs, structure_cache, job_queue)
- [ ] `[S]` Create `backend/db/__init__.py`
- [ ] `[M]` Create `backend/middleware/error_handler.py` --- structured error responses
- [ ] `[S]` Create `backend/middleware/__init__.py`
- [ ] `[S]` Create `backend/routers/__init__.py`
- [ ] `[M]` Create `backend/routers/health.py` --- `/health` endpoint checking all services
- [ ] `[S]` Create `backend/utils/__init__.py`
- [ ] `[M]` Create `backend/utils/subprocess_runner.py` --- safe subprocess wrapper with timeout
- [ ] `[M]` Create `backend/utils/api_client.py` --- shared httpx client with retry + backoff

### 0.3 Frontend Skeleton
- [ ] `[M]` Scaffold Vue 3 + TypeScript + Vite project in `frontend/`
- [ ] `[S]` Install dependencies: vue-router, pinia, axios, echarts, 3dmol, tailwindcss
- [ ] `[S]` Configure `vite.config.ts` with API proxy to :8000
- [ ] `[S]` Configure `tailwind.config.js`
- [ ] `[S]` Create `frontend/src/router/index.ts` --- route definitions
- [ ] `[S]` Create `frontend/src/types/index.ts` --- TypeScript interfaces for API models
- [ ] `[S]` Create `frontend/src/api/client.ts` --- axios instance with base URL
- [ ] `[S]` Create placeholder views: `InputView.vue`, `PipelineView.vue`, `Track1View.vue`, `Track2View.vue`, `CandidateDetailView.vue`, `StructureView.vue`, `ExportView.vue`

### 0.4 Testing Setup
- [ ] `[S]` Create `tests/conftest.py` --- pytest fixtures, test DB setup
- [ ] `[S]` Create `tests/fixtures/sample.vcf` --- 10 somatic variants
- [ ] `[S]` Create `tests/fixtures/sample_expression.tsv` --- 100 genes with TPM
- [ ] `[S]` Create `tests/fixtures/sample_hla.txt` --- pre-typed HLA alleles
- [ ] `[S]` Create `frontend/vitest.config.ts`
- [ ] `[S]` Configure `ruff.toml` for Python linting
- [ ] `[S]` Configure `.eslintrc.js` for TypeScript linting

### 0.5 Scripts
- [ ] `[S]` Create `scripts/verify-setup.sh` --- checks all dependencies are installed
- [ ] `[S]` Create `scripts/dev.sh` --- starts backend + frontend dev servers
- [ ] `[S]` Create `scripts/build-blast-db.sh` --- downloads human proteome + builds BLAST DB

---

## Phase 1: Input Layer + Variant Processor

### 1.1 Parsers
- [ ] `[M]` Create `backend/parsers/__init__.py`
- [ ] `[L]` Create `backend/parsers/vcf_parser.py` --- cyvcf2-based VCF reader, extract CHROM/POS/REF/ALT/FILTER/INFO, handle multi-allelic sites, validate somatic VCF format
- [ ] `[M]` Create `backend/parsers/rnaseq_parser.py` --- TSV reader for expression matrix, validate columns (gene_id, gene_name, TPM or counts), handle both TPM and raw count formats
- [ ] `[M]` Create `backend/parsers/hla_parser.py` --- parse pre-typed HLA reports (OptiType format, generic TSV, comma-separated), validate HLA nomenclature (e.g., HLA-A*02:01)
- [ ] `[S]` Write unit tests for `vcf_parser.py` using `tests/fixtures/sample.vcf`
- [ ] `[S]` Write unit tests for `rnaseq_parser.py` using `tests/fixtures/sample_expression.tsv`
- [ ] `[S]` Write unit tests for `hla_parser.py` using `tests/fixtures/sample_hla.txt`

### 1.2 Variant Processor
- [ ] `[S]` Create `backend/engine/__init__.py`
- [ ] `[S]` Create `backend/engine/shared/__init__.py`
- [ ] `[L]` Create `backend/engine/shared/variant_processor.py` --- Ensembl VEP REST API annotation, somatic filter (PASS variants only), consequence classification (missense, frameshift, splice, synonymous), mutation type tagging
- [ ] `[M]` Write integration test for variant_processor with mocked VEP API response
- [ ] `[S]` Create `backend/engine/shared/pipeline_runner.py` --- step-by-step executor with checkpoint/resume logic, state persistence to SQLite

### 1.3 Input Schemas
- [ ] `[M]` Create `backend/models/__init__.py`
- [ ] `[M]` Create `backend/models/input_schemas.py` --- Pydantic models: UploadRequest, SessionConfig, ValidationReport, HLAConfig, FileFormatEnum

### 1.4 Session Management
- [ ] `[M]` Create `backend/db/session_repository.py` --- CRUD for sessions table (create, get, list, update status)
- [ ] `[M]` Create `backend/queue/job_queue.py` --- SQLite-backed async job tracker (create job, update status, get pending, get by session)
- [ ] `[S]` Create `backend/queue/__init__.py`

### 1.5 Input Router
- [ ] `[L]` Create `backend/routers/input.py`:
  - [ ] `POST /input/upload` --- multipart file upload (VCF + RNA-seq), save to `/data/uploads/`, create session
  - [ ] `POST /input/validate` --- run parsers on uploaded files, return validation report
  - [ ] `POST /input/run` --- start pipeline execution, create job in queue
- [ ] `[M]` Write integration tests for input router (upload, validate, run)

### 1.6 Validation Milestone
- [ ] `[L]` End-to-end test: upload sample VCF + RNA-seq -> validate -> get annotated variant list from VEP

---

## Phase 2: Track 1 Core (Neoantigen)

### 2.1 HLA Typing
- [ ] `[S]` Create `backend/engine/track1/__init__.py`
- [ ] `[L]` Create `backend/engine/track1/hla_typer.py` --- OptiType subprocess wrapper (run in Docker), parse output (HLA-A, HLA-B, HLA-C alleles), handle pre-typed HLA input bypass
- [ ] `[M]` Write unit test with mocked OptiType output

### 2.2 Neoantigen Generation
- [ ] `[XL]` Create `backend/engine/track1/neoantigen_engine.py` --- HTTP call to pVACtools sidecar container (:8001), send annotated VCF path + HLA alleles, receive candidate peptide list (8-11mer MHC-I, 13-25mer MHC-II), filter by mutation type (missense, frameshift, splice only)
- [ ] `[M]` Create `docker/pvactools_sidecar.py` --- thin Flask app wrapping pVACtools CLI, endpoints: POST /run, GET /health, GET /status/{job_id}
- [ ] `[M]` Write integration test with mocked pVACtools sidecar response

### 2.3 Binding Affinity
- [ ] `[L]` Create `backend/engine/track1/binding_scorer.py` --- NetMHCpan subprocess call, parse output (IC50 nM, %Rank per peptide-HLA pair), classify: strong binder (<500nM), weak binder (500-5000nM), non-binder (>5000nM), normalize scores
- [ ] `[M]` Write unit test with sample NetMHCpan output file

### 2.4 Expression Filter
- [ ] `[M]` Create `backend/engine/track1/expression_filter.py` --- match neoantigen source genes to RNA-seq TPM values, filter: TPM > 1 = expressed (keep), TPM < 1 = discard, normalize expression scores
- [ ] `[S]` Write unit test

### 2.5 Track 1 Schemas
- [ ] `[M]` Create `backend/models/track1_schemas.py` --- Pydantic models: NeoantigenCandidate, HLATypingResult, BindingAffinityResult, ExpressionFilterResult, Track1Status, Track1Results

### 2.6 Track 1 Data Storage
- [ ] `[M]` Create `backend/db/result_repository.py` --- CRUD for track1_candidates and track2_candidates tables (create batch, get by session, get by ID, update scores)

### 2.7 Track 1 Router
- [ ] `[L]` Create `backend/routers/track1.py`:
  - [ ] `GET /track1/status/{session_id}` --- step-by-step progress with timestamps
  - [ ] `GET /track1/results/{session_id}` --- ranked neoantigen table with filters (min_score, max_ic50, risk_flag)
  - [ ] `GET /track1/candidate/{id}` --- full candidate detail with all scores
- [ ] `[M]` Write integration tests for track1 router

### 2.8 Validation Milestone
- [ ] `[L]` End-to-end test: sample VCF + RNA-seq -> HLA typing -> pVACtools -> NetMHCpan -> expression filter -> neoantigen candidate list with IC50 scores

---

## Phase 3: AlphaFold Integration

### 3.1 Structure Prediction Clients
- [ ] `[L]` Create `backend/engine/shared/structure_engine.py`:
  - [ ] ESMFold API client (HuggingFace inference API) --- submit sequence, receive PDB
  - [ ] AlphaFold3 server client --- submit peptide + HLA sequences, poll for result, download PDB
  - [ ] ColabFold API client --- fallback, submit sequence, receive PDB
  - [ ] Unified interface: `predict_structure(sequence, service="auto")` with fallback chain

### 3.2 Structure Cache
- [ ] `[M]` Create `backend/cache/__init__.py`
- [ ] `[M]` Create `backend/cache/structure_cache.py` --- SHA256 hash of input sequence as key, check cache before API call, store PDB file path + pLDDT score, never re-run same sequence

### 3.3 AlphaFold Queue
- [ ] `[L]` Create `backend/queue/af_queue.py` --- rate-limit aware queue for AF3 (20 jobs/day), rolling 24-hour window tracking in SQLite, auto-fallback to ColabFold when quota exhausted, retry failed jobs once, priority queue (top candidates first)
- [ ] `[M]` Write unit tests for quota tracking logic

### 3.4 PDB Parser
- [ ] `[S]` Create `backend/parsers/pdb_parser.py` --- BioPython PDB reader, calculate SASA (solvent-accessible surface area) per residue, compute exposed residue percentage (TCR contact availability)
- [ ] `[S]` Write unit test with sample PDB structure

### 3.5 AlphaFold Schemas
- [ ] `[M]` Create `backend/models/structure_schemas.py` --- Pydantic models: AlphaFoldJob, StructurePredictionResult, SASAResult, QueueStatus

### 3.6 AlphaFold Router
- [ ] `[M]` Create `backend/routers/alphafold.py`:
  - [ ] `GET /alphafold/queue` --- queue positions, remaining quota, ETAs
  - [ ] `GET /alphafold/job/{job_id}` --- job status + PDB download link
- [ ] `[S]` Write integration tests

### 3.7 Validation Milestone
- [ ] `[L]` End-to-end test: top-5 neoantigen candidates -> ESMFold API -> PDB files downloaded -> SASA calculated -> cache populated

---

## Phase 4: Track 1 Complete

### 4.1 Immunogenicity Scoring
- [ ] `[L]` Create `backend/engine/track1/immunogenicity_scorer.py` --- DeepImmuno local GPU inference (GTX1650, 4GB VRAM), IEDB Immunogenicity API fallback if GPU OOM, input: peptide + HLA allele, output: immunogenicity score 0-1
- [ ] `[M]` Write unit test with both local and API paths

### 4.2 Cross-Reactivity
- [ ] `[L]` Create `backend/engine/track1/cross_reactivity_engine.py`:
  - [ ] BLAST search against human proteome (docker exec blast container)
  - [ ] Classify: >60% identity = high risk, 40-60% = moderate, <40% = low
  - [ ] For high-risk: ESMFold structural comparison (TM-score) to rescue false positives
- [ ] `[M]` Write integration test with mocked BLAST output

### 4.3 Track 1 Ranker
- [ ] `[M]` Create `backend/engine/track1/track1_ranker.py` --- implement scoring formula from v1 plan Section 12:
  - [ ] binding_affinity_score (IC50 normalized: 0nM=1.0, 500nM=0.5, 5000nM=0.0)
  - [ ] structural_fit_score (pLDDT/90 + SASA exposure)
  - [ ] immunogenicity_score (DeepImmuno 0-1)
  - [ ] expression_score (TPM/100 capped at 1.0)
  - [ ] cross_reactivity_penalty (low=0.0, moderate=0.3, high=0.8)
  - [ ] Weighted sum * (1 - cross_reactivity_penalty)
- [ ] `[M]` Write unit tests for scoring formula with edge cases (null pLDDT, zero TPM, high cross-reactivity)

### 4.4 Validation Milestone
- [ ] `[L]` End-to-end test: full Track 1 pipeline -> complete scored + ranked neoantigen table with all columns

---

## Phase 5: Track 2 Core (Drug Target)

### 5.1 Driver Gene Identification
- [ ] `[S]` Create `backend/engine/track2/__init__.py`
- [ ] `[L]` Create `backend/engine/track2/driver_gene_engine.py` --- R subprocess via docker exec (r-engine container), run dNdScv on somatic VCF, parse output: driver genes with q-value < 0.1, per-gene selection pressure score, exclude passenger mutations
- [ ] `[M]` Create `docker/dndscv_runner.R` --- R script that accepts VCF path and outputs JSON
- [ ] `[M]` Write integration test with mocked R output

### 5.2 Mutant Protein Structure
- [ ] `[M]` Uses `engine/shared/structure_engine.py` (from Phase 3) for ESMFold calls
- [ ] `[M]` Create helper in `backend/utils/sequence_utils.py` --- apply mutation to wildtype protein sequence (fetch from UniProt), generate both wildtype and mutant FASTA
- [ ] `[S]` Write unit test for mutation application logic

### 5.3 Pocket Detection
- [ ] `[L]` Create `backend/engine/track2/pocket_engine.py` --- fpocket subprocess via docker exec (fpocket container), parse output: detected pockets with volume, druggability score, hydrophobicity, filter: druggability > 0.5 = druggable
- [ ] `[M]` Write integration test with sample PDB file

### 5.4 Pathway Mapping
- [ ] `[M]` Create `backend/engine/track2/pathway_engine.py` --- Reactome REST API client, input: driver gene list, output: dysregulated pathways + hierarchy, over-representation p-value per pathway, pathway centrality score for ranking
- [ ] `[S]` Write unit test with mocked Reactome response

### 5.5 Drug Matching
- [ ] `[L]` Create `backend/engine/track2/drug_matcher.py`:
  - [ ] ChEMBL API client --- query by target gene, get bioactivity data + drug SMILES
  - [ ] DGIdb API client --- curated drug-gene interactions
  - [ ] Merge results, prioritize: approved > phase3 > phase2 > preclinical
  - [ ] Exclude preclinical-only (insufficient evidence)
- [ ] `[M]` Write unit tests with mocked API responses

### 5.6 Toxicity Pre-filter
- [ ] `[M]` Create `backend/engine/track2/toxicity_engine.py` --- pkCSM REST API client, input: drug SMILES, output: AMES toxicity, hERG inhibition, hepatotoxicity, BBB penetration, flag toxic compounds (don't discard, rank lower)
- [ ] `[S]` Write unit test with mocked pkCSM response

### 5.7 Normal Tissue Expression
- [ ] `[M]` Create `backend/engine/track2/gtex_engine.py` --- GTEx REST API client, input: target gene, output: TPM across 54 normal tissue types, flag high expression in critical tissues (heart, brain, liver, kidney) as ON-TARGET OFF-TUMOR risk
- [ ] `[S]` Write unit test with mocked GTEx response

### 5.8 Track 2 Ranker
- [ ] `[M]` Create `backend/engine/track2/track2_ranker.py` --- implement scoring formula from v1 plan Section 12:
  - [ ] druggability_score (fpocket 0-1)
  - [ ] evidence_level (approved=1.0, phase3=0.8, phase2=0.5, preclinical=0.2)
  - [ ] toxicity_penalty (count of flags * 0.2, max 0.8)
  - [ ] normal_tissue_penalty (low=0.0, moderate=0.2, high=0.5)
  - [ ] Weighted product: (drug*0.35 + evidence*0.35) * (1-tox) * (1-tissue)
- [ ] `[M]` Write unit tests for scoring formula with edge cases

### 5.9 Track 2 Schemas + Router
- [ ] `[M]` Create `backend/models/track2_schemas.py` --- Pydantic models: DrugTargetCandidate, DriverGeneResult, PocketResult, DrugMatch, ToxicityReport, Track2Status, Track2Results
- [ ] `[L]` Create `backend/routers/track2.py`:
  - [ ] `GET /track2/status/{session_id}` --- step progress
  - [ ] `GET /track2/results/{session_id}` --- ranked drug-target table with filters
  - [ ] `GET /track2/candidate/{id}` --- full candidate detail
- [ ] `[M]` Write integration tests for track2 router

### 5.10 Validation Milestone
- [ ] `[L]` End-to-end test: sample VCF -> dNdScv -> ESMFold -> fpocket -> Reactome -> ChEMBL/DGIdb -> pkCSM -> GTEx -> ranked drug-target table

---

## Phase 6: Frontend Core

### 6.1 Project Setup
- [ ] `[M]` Finalize Vue 3 + TypeScript + Vite configuration
- [ ] `[M]` Set up Tailwind CSS with custom theme (dark sidebar, teal Track 1 accent #00897B, indigo Track 2 accent #3949AB, risk red #E53935, pass green #43A047)
- [ ] `[S]` Create `frontend/src/App.vue` with sidebar layout + router-view

### 6.2 TypeScript Interfaces
- [ ] `[M]` Create `frontend/src/types/session.ts` --- Session, UploadConfig, ValidationReport
- [ ] `[M]` Create `frontend/src/types/track1.ts` --- NeoantigenCandidate, HLAResult, Track1Results
- [ ] `[M]` Create `frontend/src/types/track2.ts` --- DrugTargetCandidate, DriverGene, Track2Results
- [ ] `[S]` Create `frontend/src/types/pipeline.ts` --- PipelineStep, PipelineStatus, StepProgress
- [ ] `[S]` Create `frontend/src/types/structure.ts` --- AlphaFoldJob, StructureResult

### 6.3 API Client Modules
- [ ] `[M]` Create `frontend/src/api/inputApi.ts` --- upload, validate, run
- [ ] `[M]` Create `frontend/src/api/track1Api.ts` --- status, results, candidate detail
- [ ] `[M]` Create `frontend/src/api/track2Api.ts` --- status, results, candidate detail
- [ ] `[S]` Create `frontend/src/api/alphaFoldApi.ts` --- queue, job status
- [ ] `[S]` Create `frontend/src/api/resultApi.ts` --- unified results, export
- [ ] `[M]` Create `frontend/src/api/wsClient.ts` --- WebSocket connection manager, auto-reconnect, event parsing

### 6.4 Pinia Stores
- [ ] `[M]` Create `frontend/src/stores/sessionStore.ts` --- upload state, active session ID, validation status
- [ ] `[M]` Create `frontend/src/stores/pipelineStore.ts` --- WebSocket-driven step progress, log buffer
- [ ] `[M]` Create `frontend/src/stores/track1Store.ts` --- neoantigen results, filters, selected candidate
- [ ] `[M]` Create `frontend/src/stores/track2Store.ts` --- drug target results, filters, selected candidate
- [ ] `[S]` Create `frontend/src/stores/structureStore.ts` --- AlphaFold job status, PDB data

### 6.5 Shared Components
- [ ] `[S]` Create `frontend/src/components/shared/PageHeader.vue` --- title + breadcrumbs
- [ ] `[S]` Create `frontend/src/components/shared/StatusBadge.vue` --- colored status indicator
- [ ] `[S]` Create `frontend/src/components/shared/ExportButton.vue` --- PDF/JSON/HTML export trigger
- [ ] `[M]` Create `frontend/src/components/shared/Sidebar.vue` --- navigation with track/step selector
- [ ] `[S]` Create `frontend/src/components/shared/DisclaimerBanner.vue` --- "Research grade output. Not for clinical use."
- [ ] `[S]` Create `frontend/src/components/shared/LoadingSkeleton.vue` --- skeleton placeholder
- [ ] `[S]` Create `frontend/src/components/shared/ErrorBoundary.vue` --- graceful error display + retry

### 6.6 Input View
- [ ] `[L]` Create `frontend/src/views/InputView.vue` --- guided wizard layout (step 1: VCF, step 2: RNA-seq, step 3: HLA config, step 4: track selection, step 5: confirm + run)
- [ ] `[M]` Create `frontend/src/components/upload/FileDropZone.vue` --- drag-and-drop file upload with progress bar
- [ ] `[M]` Create `frontend/src/components/upload/FormatValidator.vue` --- client-side format check feedback (file size, extension, header row preview)
- [ ] `[M]` Create `frontend/src/components/upload/HLAInput.vue` --- manual HLA allele entry with autocomplete + validation (HLA-A*02:01 format)

### 6.7 Pipeline View
- [ ] `[L]` Create `frontend/src/views/PipelineView.vue` --- live progress across all steps, WebSocket-driven updates
- [ ] `[M]` Create `frontend/src/components/pipeline/StepProgress.vue` --- per-step status indicator (pending/running/completed/failed) with time elapsed + ETA
- [ ] `[M]` Create `frontend/src/components/pipeline/QueueStatus.vue` --- AlphaFold job queue viewer (position, quota remaining, ETA)
- [ ] `[M]` Create `frontend/src/components/pipeline/LogViewer.vue` --- real-time scrolling log output, filterable by step

### 6.8 Results Views
- [ ] `[L]` Create `frontend/src/views/Track1View.vue` --- neoantigen results page with ranked table + filters
- [ ] `[L]` Create `frontend/src/views/Track2View.vue` --- drug target results page with ranked table + filters
- [ ] `[L]` Create `frontend/src/components/results/RankedTable.vue` --- sortable by any column, filterable by risk flag, score threshold slider, pagination
- [ ] `[M]` Create `frontend/src/components/results/RiskBadge.vue` --- risk level indicator (high=red, moderate=amber, low=green)
- [ ] `[M]` Create `frontend/src/components/results/EvidenceBadge.vue` --- clinical evidence level chip (approved, phase3, phase2, preclinical)
- [ ] `[M]` Create `frontend/src/components/results/ScoreBar.vue` --- composite score visual bar with weighted segment breakdown
- [ ] `[M]` Create `frontend/src/components/results/CandidateCard.vue` --- summary card for top candidates (preview before detail view)

### 6.9 Candidate Detail View
- [ ] `[XL]` Create `frontend/src/views/CandidateDetailView.vue` --- deep-dive view for single candidate:
  - [ ] Score breakdown panel (all weights visible)
  - [ ] Evidence links panel (ChEMBL, DGIdb, Reactome)
  - [ ] Risk flags panel (cross-reactivity, toxicity, normal tissue)
  - [ ] Structure viewer embed (3Dmol.js, built in Phase 7)
  - [ ] Expression data panel (TPM, tissue distribution)

### 6.10 WebSocket Integration
- [ ] `[L]` Create `backend/routers/ws.py` --- WebSocket endpoint `/ws/pipeline/{session_id}`, push step transitions + progress + log lines
- [ ] `[M]` Wire WebSocket client in `pipelineStore.ts` to receive and display real-time updates
- [ ] `[S]` Handle WebSocket reconnection on browser refresh

### 6.11 Validation Milestone
- [ ] `[L]` End-to-end browser test: upload files -> see pipeline progress -> view Track 1 + Track 2 results -> click candidate detail

---

## Phase 7: Structure Viewer + Charts

### 7.1 3D Structure Viewer
- [ ] `[L]` Create `frontend/src/components/structure/MolViewer.vue` --- 3Dmol.js wrapper, load PDB from backend, configurable rendering (cartoon, stick, surface), residue coloring by pLDDT confidence
- [ ] `[M]` Create `frontend/src/components/structure/PocketHighlight.vue` --- fpocket binding site overlay on 3Dmol viewer, highlight pocket residues, show volume + druggability score
- [ ] `[M]` Create `frontend/src/components/structure/StructureCompare.vue` --- side-by-side wildtype vs mutant structure viewer, synchronized rotation, highlight mutation site

### 7.2 Structure View Page
- [ ] `[L]` Create `frontend/src/views/StructureView.vue` --- full-page structure viewer with controls panel, integrates MolViewer + PocketHighlight + StructureCompare

### 7.3 Charts
- [ ] `[M]` Create `frontend/src/components/charts/ScoreDistribution.vue` --- ECharts histogram of candidate scores (Track 1 and Track 2), highlight selected candidate position, configurable bins
- [ ] `[L]` Create `frontend/src/components/charts/ExpressionHeatmap.vue` --- ECharts heatmap of gene expression across samples/tissues, row = gene, column = tissue, color = TPM intensity
- [ ] `[L]` Create `frontend/src/components/charts/PathwayNetwork.vue` --- ECharts graph or D3 force-directed layout of Reactome pathway network, nodes = genes/pathways, edges = interactions, highlight driver genes + druggable nodes

### 7.4 Responsive Layout
- [ ] `[M]` Ensure all chart components resize correctly on window resize
- [ ] `[M]` Ensure 3Dmol viewer handles container size changes
- [ ] `[S]` Add chart loading states (skeleton while data fetches)

### 7.5 Validation Milestone
- [ ] `[M]` Visual test: structure viewer renders PDB, pocket highlighted, charts display with sample data

---

## Phase 8: Export + Polish

### 8.1 PDF Export Engine
- [ ] `[L]` Create `backend/engine/shared/report_engine.py` --- WeasyPrint PDF generation, Jinja2 template rendering, embed charts as base64 images
- [ ] `[M]` Create `backend/utils/pdf_templates/track1_report.html` --- Track 1 neoantigen report template (ranked table, top-5 candidate details, score distributions)
- [ ] `[M]` Create `backend/utils/pdf_templates/track2_report.html` --- Track 2 drug target report template (ranked table, drug matches, toxicity flags)
- [ ] `[M]` Create `backend/utils/pdf_templates/unified_report.html` --- Combined report with both tracks, executive summary, methodology notes

### 8.2 Export Router
- [ ] `[M]` Create `backend/routers/results.py`:
  - [ ] `GET /results/unified/{session_id}` --- merged ranked output from both tracks
  - [ ] `GET /results/export/{session_id}?format=pdf` --- PDF report download
  - [ ] `GET /results/export/{session_id}?format=json` --- JSON data export
  - [ ] `GET /results/export/{session_id}?format=html` --- self-contained HTML report
- [ ] `[S]` Write integration tests for export endpoints

### 8.3 Export View
- [ ] `[M]` Create `frontend/src/views/ExportView.vue` --- report generation page with format selection (PDF/JSON/HTML), track selection, download button, preview

### 8.4 UI Polish
- [ ] `[S]` Add disclaimer banner to all result views (`Track1View`, `Track2View`, `CandidateDetailView`, `ExportView`)
- [ ] `[M]` Add loading skeleton states to all views
- [ ] `[M]` Add empty states to all list views ("No results yet", "Upload data to begin")
- [ ] `[M]` Add error boundary components with retry buttons
- [ ] `[S]` Add keyboard shortcuts: arrow keys for table navigation, Escape to go back
- [ ] `[S]` Add favicon and page titles per view

### 8.5 Sample Data
- [ ] `[M]` Create a small sample data subset from Sid's dataset for demo mode
- [ ] `[S]` Create demo mode trigger in InputView (skip upload, use bundled data)
- [ ] `[M]` Pre-compute sample results for demo mode (so demo runs instantly)

### 8.6 Documentation
- [ ] `[M]` Update README.md with final screenshots and verified quick start
- [ ] `[S]` Create `CONTRIBUTING.md` with development setup + code style guide
- [ ] `[S]` Create `CHANGELOG.md` with v1.0.0 entry
- [ ] `[S]` Add inline code comments for complex scoring logic

### 8.7 Final Validation
- [ ] `[L]` Full end-to-end test: upload -> pipeline -> Track 1 results -> Track 2 results -> candidate detail with structure -> export PDF + JSON
- [ ] `[M]` Cross-browser test: Chrome, Firefox, Edge
- [ ] `[M]` Docker clean build test: clone fresh -> docker compose up -> everything works
- [ ] `[S]` Verify disclaimer banner appears on ALL result pages
- [ ] `[S]` Verify all external API calls have retry + timeout handling
- [ ] `[S]` Run `ruff check` + `mypy` + `eslint` with zero errors

---

## Summary

| Phase | Tasks | Complexity | Dependencies |
|---|---|---|---|
| Phase 0: Scaffolding | 35 | M | None |
| Phase 1: Input + Variants | 20 | L | Phase 0 |
| Phase 2: Track 1 Core | 18 | XL | Phase 1 |
| Phase 3: AlphaFold | 14 | XL | Phase 1 |
| Phase 4: Track 1 Complete | 8 | L | Phase 2, Phase 3 |
| Phase 5: Track 2 Core | 24 | XL | Phase 1, (Phase 3 for structure_engine) |
| Phase 6: Frontend Core | 42 | XL | Phase 2 + Phase 5 API contracts |
| Phase 7: Structure + Charts | 12 | L | Phase 6 |
| Phase 8: Export + Polish | 22 | L | Phase 6, Phase 7 |
| **Total** | **~195** | | |
