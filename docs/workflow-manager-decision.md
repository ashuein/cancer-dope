# Workflow Manager Decision

**Decision:** Use **Nextflow** as the selected workflow manager for the PrecisionOncology analysis runtime.

**Status:** Accepted for implementation planning.

---

## 1. Context

The platform needs to orchestrate heterogeneous oncology analysis modules, including clinical timeline processing, neoantigen analysis, drug-target ranking, bulk RNA, single-cell RNA, GSEA, CNV, genome-browser manifests, imaging, and spatial outputs. These modules have different runtime profiles, container requirements, input formats, and retry behavior.

The workflow manager must support:

- containerized execution,
- resumable and checkpointed runs,
- module-level parallelism,
- reproducible configuration,
- local development with a path to larger compute backends,
- clear mapping between workflow tasks and application provenance records,
- file-oriented outputs that can be registered as artifacts.

---

## 2. Decision

Nextflow is selected as the canonical workflow manager.

The application should treat Nextflow as the execution layer for analysis work, while the API remains the system of record for cases, runs, steps, artifacts, visualization datasets, and user-facing status. The API should create an `AnalysisRun`, prepare an input manifest, invoke or enqueue a Nextflow run, then ingest workflow status and output manifests back into the metadata and artifact registry layers.

---

## 3. Why Nextflow

Nextflow is a strong fit because it provides:

- native support for process-oriented pipelines,
- straightforward container integration,
- resumability through cached work directories,
- parallel execution of independent processes,
- clear input and output channel semantics,
- configuration profiles for local and future compute environments,
- broad adoption in bioinformatics workflows.

These capabilities match the repository's planned architecture: Dockerized modules, case-scoped runs, checkpointable steps, versioned artifacts, and page-ready derived datasets.

---

## 4. Runtime Boundary

### API responsibilities

- Own case, input, run, step, artifact, and visualization metadata.
- Validate user requests and module selection.
- Create immutable run configuration snapshots.
- Generate the input manifest passed to Nextflow.
- Track user-facing run status.
- Register artifacts and visualization datasets emitted by workflows.
- Serve page-ready data to the frontend.

### Nextflow responsibilities

- Execute module processes.
- Resolve process dependencies.
- Run containerized tools.
- Manage work directories and resumable task execution.
- Publish module outputs into run-scoped output directories.
- Emit machine-readable output manifests for artifact registration.

### Shared contract

The API and Nextflow runtime should exchange manifests rather than direct database writes from workflow processes. This keeps provenance ownership in the API while preserving workflow portability.

---

## 5. Proposed Run Handoff

When a run starts, the API should create a handoff package with:

```json
{
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

Nextflow should read this package, run selected modules, and write module output manifests back under the run directory.

---

## 6. Step and Artifact Mapping

Each Nextflow process that produces user-facing output should map to a `StepRun` record. The process should emit an output manifest that includes:

- step name,
- module name,
- output file paths,
- declared artifact types,
- file formats,
- checksums if computed by the process,
- derived dataset paths when produced,
- warnings and non-fatal validation messages.

The API should ingest these manifests and create or update `Artifact` and `VisualizationDataset` records.

---

## 7. Parallelism Model

Nextflow should coordinate module-level and process-level parallelism. The planned parallel work model is:

- Clinical timeline import can run independently from omics modules.
- Bulk RNA and scRNA imports can run independently if their inputs are available.
- GSEA depends on differential expression inputs from bulk RNA or scRNA.
- CNV and BAM manifest preparation can run independently after required genomic files are registered.
- Imaging and spatial imports can run independently from sequencing modules.
- Data catalog generation depends on artifact registration and should run after selected modules complete.
- Frontend dataset derivation should run after the artifacts needed by each page are present.

This model allows early pages to become available before every module in a run has completed.

---

## 8. Failure and Resume Expectations

- A failed process should update its corresponding `StepRun` to failed with a useful error summary.
- Non-dependent modules should continue when safe.
- Retrying a run should use Nextflow resume behavior where possible.
- A resumed or repeated run must not overwrite previous run artifacts.
- Superseded artifacts should remain traceable unless an explicit retention policy removes them.

---

## 9. Alternatives Considered

### Plain Python workers

Plain workers are simple to start with, but they would require custom orchestration, retries, dependency handling, resume behavior, and execution provenance.

### Celery-only task graph

Celery can manage asynchronous jobs, but complex file-oriented bioinformatics workflows still need substantial custom structure for process dependency management, caching, and reproducibility.

### Snakemake

Snakemake is also a credible bioinformatics workflow manager. Nextflow is selected here because its process/channel model, configuration profiles, and common containerized deployment patterns align well with the desired module boundaries and future compute portability.

---

## 10. Consequences

- The implementation should add a Nextflow project layout when workflow code begins.
- Module authors should define process inputs and outputs through explicit manifests.
- The API must include a workflow invocation layer or queue integration.
- Tests should cover both metadata provenance and workflow output manifest ingestion.
- Documentation should refer to Nextflow as the selected workflow manager unless the decision is formally revisited.
