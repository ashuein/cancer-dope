# Implementation Task List

**Status:** Planning documentation only. No backend, workflow, or application code is changed by this document.

This task list decomposes the PrecisionOncology platform into parallel workstreams that can proceed without blocking each other. The selected workflow manager is **Nextflow**. Nextflow should be treated as the canonical execution layer for long-running analysis modules, checkpointed tasks, containerized tools, and resumable case runs.

---

## 1. Guiding Delivery Principles

- Keep implementation incremental and module-oriented.
- Prefer processed import paths before raw-data pipelines for heavy omics modules.
- Register every generated file as a versioned artifact before exposing it to the portal.
- Derive frontend datasets from artifacts instead of binding pages directly to raw analysis outputs.
- Maintain reproducibility through pinned containers, checksums, run configuration snapshots, and provenance records.
- Do not allow visualization pages to display data that cannot be traced back to a case, run, step, and artifact.

---

## 2. Parallel Workstream Plan

### Workstream A — Product and Documentation Backbone

**Ownership:** Architecture, documentation, acceptance criteria.

Tasks:
- Finalize module-level acceptance criteria for each planned visualization page.
- Maintain artifact taxonomy and page dependency mapping.
- Define sample case personas and minimal demo datasets.
- Keep README documentation links current as implementation documents are added.
- Maintain glossary for `Case`, `AnalysisRun`, `StepRun`, `Artifact`, and `VisualizationDataset`.

Deliverables:
- Architecture documentation updates.
- Implementation checklist updates.
- Demo-data acceptance matrix.

Dependencies:
- None. This workstream can continue throughout the project.

### Workstream B — Metadata, Provenance, and Artifact Registry

**Ownership:** Data model, persistence, artifact lifecycle.

Tasks:
- Define relational models for cases, runs, steps, artifacts, visualization datasets, and external calls.
- Implement artifact registration with checksum, format, type, path, status, and provenance fields.
- Add status transitions for queued, running, completed, failed, skipped, and superseded states.
- Add artifact retention and replacement rules.
- Add catalog query patterns for page and download views.

Deliverables:
- Metadata schema migrations.
- Artifact registry service.
- Provenance query helpers.

Dependencies:
- Data contracts in `docs/data-contracts.md`.

### Workstream C — Nextflow Workflow Runtime

**Ownership:** Workflow execution, process orchestration, resumability.

Tasks:
- Establish Nextflow as the selected workflow manager for analysis modules.
- Define the boundary between API run records and Nextflow run execution.
- Create a standard handoff package from API to Nextflow: case ID, run ID, input manifest, module selection, output root, reference root, and configuration snapshot.
- Define Nextflow process labels for compute class, container image, memory, CPU, and retry policy.
- Define callback or polling strategy for StepRun updates.
- Define how Nextflow work directories and published artifacts map into the artifact registry.

Deliverables:
- Nextflow project skeleton when implementation begins.
- Shared module interface for input manifests and output manifests.
- Operational runbook for resume and failure handling.

Dependencies:
- Artifact registry contract.
- Storage layout decision.

### Workstream D — Backend API and Run Control

**Ownership:** Case APIs, upload/register APIs, run APIs, visualization dataset APIs.

Tasks:
- Implement case CRUD and summary endpoints.
- Implement input upload or registration endpoints.
- Implement run creation with module selection and configuration capture.
- Implement run status, step status, and event endpoints.
- Implement artifact listing and download endpoints.
- Implement visualization dataset lookup endpoints.

Deliverables:
- API endpoints matching the planned surface in README.
- Request and response schemas aligned with data contracts.
- API tests for provenance and access patterns.

Dependencies:
- Metadata and artifact registry.
- Nextflow handoff contract.

### Workstream E — Analysis Modules

**Ownership:** Module-specific transformations and containerized tools.

Tasks:
- Implement processed import modules first for clinical timeline, bulk RNA, scRNA, GSEA, CNV, BAM manifest, vaccine overlap, imaging, and spatial data.
- Add raw-mode modules after processed imports are stable.
- Emit normalized artifacts and module-level output manifests.
- Add module smoke tests using small fixture datasets.
- Add validation of required input columns, file formats, and reference IDs.

Deliverables:
- Containerized module implementations.
- Nextflow process definitions.
- Module output manifests.

Dependencies:
- Nextflow runtime conventions.
- Data contracts.

### Workstream F — Frontend Portal and Visualization Pages

**Ownership:** Vue routes, page components, visualization state, downloads.

Tasks:
- Implement case list and case overview pages.
- Implement page shells for timeline, bulk RNA, scRNA, GSEA, CNV, BAM, vaccines, imaging, spatial, track 1, track 2, and catalog.
- Bind pages to visualization dataset APIs rather than raw artifacts.
- Add loading, empty, unavailable, and error states per module.
- Add data provenance panels that expose source run and artifact metadata.

Deliverables:
- Route-level pages.
- Reusable visualization components.
- Provenance and catalog UI patterns.

Dependencies:
- Visualization dataset contracts.
- Backend API endpoints.

### Workstream G — DevOps, Packaging, and Demo Environment

**Ownership:** Docker Compose, local development, CI, release artifacts.

Tasks:
- Add local service profiles for API, web, metadata DB, artifact storage, and workflow execution.
- Define container image build and tag conventions for each module.
- Add CI checks for backend, frontend, docs, and workflow linting.
- Add demo data loading command once minimal fixtures exist.
- Add backup and cleanup guidance for local artifact volumes.

Deliverables:
- Reproducible local stack.
- CI pipeline.
- Demo run instructions.

Dependencies:
- Runtime decisions and module skeletons.

---

## 3. Suggested Milestones

### Milestone 0 — Planning Baseline

- [ ] Confirm Nextflow as selected workflow manager.
- [ ] Confirm canonical entities and data contracts.
- [ ] Confirm artifact taxonomy and page dependency map.
- [ ] Confirm processed-import-first delivery path.

### Milestone 1 — Case, Run, and Artifact Foundation

- [ ] Implement metadata schema.
- [ ] Implement case and run APIs.
- [ ] Implement artifact registry.
- [ ] Implement catalog endpoint using registered artifacts.
- [ ] Add smoke tests for provenance chain integrity.

### Milestone 2 — Nextflow Runtime Skeleton

- [ ] Add Nextflow project layout.
- [ ] Add API-to-Nextflow handoff manifest contract.
- [ ] Add a no-op or fixture workflow that produces a registered artifact.
- [ ] Add resume and failure-state documentation.
- [ ] Add workflow status propagation into StepRun records.

### Milestone 3 — First Functional Module Slice

- [ ] Implement clinical timeline processed import.
- [ ] Generate timeline visualization dataset.
- [ ] Render case overview and timeline pages.
- [ ] Register all module outputs with checksums and provenance.
- [ ] Add fixture-backed tests.

### Milestone 4 — Omics and Track Expansion

- [ ] Add bulk RNA processed import.
- [ ] Add scRNA processed import.
- [ ] Add GSEA derived outputs.
- [ ] Add track 1 neoantigen result import or pipeline slice.
- [ ] Add track 2 drug-target result import or pipeline slice.

### Milestone 5 — Browser, Imaging, and Catalog Completion

- [ ] Add CNV SEG and BigWig support.
- [ ] Add BAM/BAI manifest support.
- [ ] Add image tile manifest support.
- [ ] Add spatial bundle support.
- [ ] Complete data catalog and download flows.

---

## 4. Cross-Workstream Integration Checkpoints

At the end of each milestone, verify:

- Every visible page has a declared visualization dataset contract.
- Every visualization dataset points to one or more registered artifacts.
- Every artifact points to a StepRun.
- Every StepRun points to an AnalysisRun and Case.
- Every workflow-produced file is either registered or intentionally discarded.
- Every module can be rerun without overwriting prior run artifacts.
- Every API response has a documented unavailable or empty state.

---

## 5. Out of Scope for This Planning Pass

- Backend implementation changes.
- Workflow implementation changes.
- Frontend application changes.
- Clinical validation or treatment recommendation logic.
- Production deployment hardening beyond planning notes.
