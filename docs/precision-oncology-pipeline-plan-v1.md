# PrecisionOncology Pipeline — Project Plan Document
**Version:** 1.0
**Date:** March 27, 2026
**Reference Dataset:** Sid Sijbrandij Osteosarcoma (osteosarc.com)
**Stack:** Vue 3 + Vite | Python FastAPI | SQLite | ECharts | Plotly.js
**Compute:** 48GB RAM | GTX1650 4GB VRAM | 8TB HDD | API-first for AlphaFold

---

## 1. Project Intent

An open-source, locally deployable precision oncology pipeline that accepts patient genomic data and produces ranked therapeutic hypotheses via two parallel tracks:

- **Track 1 — Neoantigen:** Identifies tumor-specific peptides for personalized vaccine or adoptive T-cell therapy design
- **Track 2 — Drug Target:** Identifies mutant protein targets with druggability assessment and toxicity pre-filtering

**Core philosophy:** Democratize the computational layer of precision oncology. Every step uses established open-source tools. The pipeline orchestrates them into a single usable workflow with a human-readable results interface. Output is explicitly research-grade — not clinical prescription.

**Reference dataset:** Sid Sijbrandij osteosarcoma multi-modal genomic data (public, GCS bucket osteosarc-genomics). Used as primary test and demo dataset.

---

## 2. System Boundaries

### 2.1 In Scope (v1)

- VCF (somatic variant) input processing
- RNA-seq expression input (processed TSV — not raw FASTQ)
- HLA typing from BAM or pre-typed input
- Track 1: Full neoantigen prediction pipeline with AlphaFold structural validation
- Track 2: Driver gene identification, pathway mapping, drug matching with toxicity filter
- AlphaFold integration via API (ESMFold/HuggingFace, AF3 server, ColabFold)
- Unified ranked results view with per-candidate evidence scoring
- Candidate detail view: structure visualization, evidence links, risk flags
- Export: ranked table PDF + JSON for each track

### 2.2 Out of Scope (v1)

- Raw FASTQ processing (too compute-heavy for local; accept processed outputs only)
- Whole genome alignment pipeline (GATK somatic calling assumed pre-run)
- scRNA-seq cell-type deconvolution (optional overlay, not core pipeline)
- Drug synthesis or experimental protocol generation
- Clinical decision support — output is explicitly research-grade
- Multi-patient comparison
- Local AlphaFold2/3 (VRAM insufficient — 4GB vs 16GB+ required)

---

## 3. Compute Architecture

### 3.1 Local vs API Allocation

| Component | Execution | Reason |
|---|---|---|
| VCF parsing + annotation | Local | CPU-only, 48GB RAM sufficient |
| HLA typing (OptiType) | Local | CPU-only |
| Neoantigen generation (pVACtools) | Local | CPU-only |
| Binding affinity (NetMHCpan) | Local | CPU binary, no GPU needed |
| Immunogenicity scoring (DeepImmuno) | Local GPU | 4GB VRAM marginal but viable |
| Cross-reactivity check | Local | CPU, proteome BLAST |
| Expression filtering | Local | Pandas on RNA-seq TSV |
| Driver gene identification (dNdScv) | Local | R subprocess |
| Pathway mapping (Reactome) | API | REST, no compute |
| Drug matching (ChEMBL, DGIdb) | API | REST, no compute |
| Toxicity filter (pkCSM) | API | REST, no compute |
| Normal tissue expression (GTEx) | API | REST, no compute |
| ESMFold (fast monomer) | HuggingFace API | 4GB VRAM insufficient locally |
| AlphaFold3 (peptide-HLA complex) | alphafoldserver.com | 20 jobs/day free |
| ColabFold (AF2 fallback) | colabfold.com API | Rate-limited fallback |
| Pocket detection (fpocket) | Local | CPU-only, runs on downloaded PDB |

### 3.2 Storage Strategy (8TB HDD)

```
Download from Sid's GCS bucket — selective only:
  VCF files (somatic variants):          ~2 GB
  RNA-seq processed TSV:                 ~50 GB
  BAM files (HLA typing subset):         ~500 GB
  AlphaFold predicted structures (PDB):  ~100 GB
  Pipeline intermediate outputs:         ~100 GB
  Total estimated:                       ~752 GB

Do NOT download:
  Raw FASTQ files (multi-TB each)
  Full WGS BAM set (15TB+)
```

---

## 4. Input Formats

| Format | Contents | Track | Required |
|---|---|---|---|
| VCF (somatic) | Called mutations vs germline | Both | Mandatory |
| RNA-seq TSV | Gene expression (TPM or counts) | Both | Mandatory |
| BAM/CRAM (subset) | Aligned reads for HLA typing | 1 | Optional if HLA pre-typed |
| HLA typing report (TXT/TSV) | Pre-typed HLA alleles | 1 | Alternative to BAM |
| scRNA-seq (10X MEX or H5) | Cell-type resolved expression | Both | Optional overlay |

---

## 5. Pipeline Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      INPUT LAYER                         │
│   VCF + RNA-seq TSV + BAM or HLA report + optional scRNA│
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  VARIANT PROCESSOR                        │
│  VCF parsing → annotation (Ensembl VEP)                  │
│  Somatic filter → consequence classification             │
│  Mutation type tagging (missense/frameshift/splice)      │
└──────────┬───────────────────────────┬───────────────────┘
           │                           │
┌──────────▼───────────┐   ┌───────────▼──────────────────┐
│      TRACK 1         │   │          TRACK 2              │
│   NEOANTIGEN         │   │       DRUG TARGET             │
│   PIPELINE           │   │       PIPELINE                │
└──────────┬───────────┘   └───────────┬──────────────────┘
           │                           │
┌──────────▼───────────────────────────▼──────────────────┐
│              ALPHAFOLD INTEGRATION LAYER                  │
│  ESMFold API → AlphaFold3 server → ColabFold fallback    │
│  fpocket local → druggability + exposure scoring         │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  UNIFIED RANKER                           │
│  Per-track scored candidates merged into single view      │
│  Evidence level tagging + risk flag overlay               │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  RESULTS INTERFACE                        │
│  Ranked table → candidate detail → structure viewer       │
│  Export: PDF + JSON per track                            │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Track 1 — Neoantigen Pipeline (Detailed)

### Step 1: HLA Typing
```
Tool:    OptiType (local, Python)
Input:   BAM file (RNA or DNA) OR pre-typed HLA report
Output:  HLA-A, HLA-B, HLA-C alleles (MHC Class I)
         HLA-DR, HLA-DQ alleles (MHC Class II — for CD4 T-cell)
Note:    If user provides pre-typed HLA, skip OptiType
```

### Step 2: Neoantigen Candidate Generation
```
Tool:    pVACtools (local, Python)
Input:   Somatic VCF (annotated) + HLA alleles
Output:  Candidate peptide list
         MHC-I:  8–11mer peptides (CD8 T-cell targets)
         MHC-II: 13–25mer peptides (CD4 T-cell targets)
Filters: Missense, frameshift, splice site mutations only
         Silent mutations excluded
```

### Step 3: Binding Affinity Prediction
```
Tool:    NetMHCpan 4.1 (local binary)
Input:   Candidate peptides + HLA alleles
Output:  IC50 (nM) per peptide-HLA pair
         %Rank (percentile vs random peptides)
Filters: IC50 < 500nM = strong binder (keep)
         IC50 500–5000nM = weak binder (flag, don't discard)
         IC50 > 5000nM = non-binder (discard)
```

### Step 4: AlphaFold — Peptide-HLA Structure
```
Tool:    AlphaFold3 server (alphafoldserver.com)
         20 jobs/day free limit — apply to top candidates only
         ColabFold API as fallback
Input:   Peptide sequence + HLA allele protein sequence
Output:  3D complex structure (PDB file)
         pLDDT confidence score per residue
Value:   Structural validation of binding affinity score
         Peptides with poor IC50 but good structural fit = rescue
         Peptides with good IC50 but poor structural fit = demote
```

### Step 5: Peptide Exposure Analysis
```
Tool:    BioPython (local) on downloaded PDB
Input:   Peptide-HLA PDB structure
Output:  Solvent-accessible surface area (SASA) per residue
         Exposed residue map (available for TCR contact)
Value:   Buried peptides cannot trigger T-cell response
         regardless of binding score — structural filter
```

### Step 6: Expression Filter
```
Tool:    Pandas (local) on RNA-seq TSV
Input:   Source gene of each neoantigen + TPM matrix
Output:  Expression-confirmed vs expression-absent flag
Filter:  TPM > 1 = expressed (keep)
         TPM < 1 = not expressed (discard — mutation not transcribed)
Bonus:   scRNA-seq overlay shows which cell types express it
```

### Step 7: Immunogenicity Scoring
```
Tool:    DeepImmuno (local, GTX1650 4GB marginal)
         IEDB Immunogenicity tool (API fallback)
Input:   Peptide sequence + HLA allele
Output:  Immunogenicity score (0–1)
Value:   Predicts whether peptide actually activates T-cells
         Beyond just binding — activation is the goal
```

### Step 8: Cross-Reactivity Check
```
Tool:    BLAST local (blastp against human proteome)
Input:   Neoantigen peptide sequence
Output:  Similarity hits in human proteome
Flag:    >60% identity to human self-peptide = high risk
         40–60% = moderate risk (flag, don't discard)
         <40% = low risk

AlphaFold layer:
  For high-risk flagged peptides:
  ESMFold API → predict self-peptide structure
  Compare structural similarity (TM-score) vs neoantigen
  Sequence similarity ≠ structural similarity
  False positives rescued here
```

### Step 9: Track 1 Ranking
```
Final Score =
  binding_affinity_score (NetMHCpan, normalized)
  × structural_fit_score (AlphaFold pLDDT + SASA)
  × immunogenicity_score (DeepImmuno)
  × expression_score (TPM normalized)
  × (1 - cross_reactivity_risk)

Output: Ranked neoantigen table
  Columns: peptide, HLA allele, IC50, rank%, 
           AF3_pLDDT, SASA_exposed%, TPM,
           immunogenicity, cross_reactivity_risk,
           final_score, risk_flag
```

---

## 7. Track 2 — Drug Target Pipeline (Detailed)

### Step 1: Driver Gene Identification
```
Tool:    dNdScv (R package, local subprocess)
Input:   Somatic VCF
Output:  Driver genes (q-value < 0.1)
         Passenger mutations excluded
         Per-gene selection pressure score
```

### Step 2: Mutant Protein Structure
```
Tool:    ESMFold via HuggingFace API (fast, CPU-viable via API)
Input:   Wildtype protein sequence + mutation applied
Output:  Wildtype PDB + Mutant PDB
Value:   Structural consequence of mutation
         Novel binding pockets created by mutation
         Conformational changes in active site
```

### Step 3: Druggability Assessment
```
Tool:    fpocket (local, CPU)
Input:   Mutant PDB structure
Output:  Detected binding pockets
         Per-pocket: volume, druggability score, hydrophobicity
Filter:  Druggability score > 0.5 = druggable (keep)
         Score < 0.5 = undruggable (flag — no binding site)
Value:   Patient-specific — same gene may be undruggable
         in wildtype but druggable in this patient's mutant
```

### Step 4: Pathway Mapping
```
Tool:    Reactome REST API
Input:   Driver gene list
Output:  Dysregulated pathways + pathway hierarchy
         Over-representation p-value per pathway
Value:   Identifies upstream pathway targets
         May find druggable pathway node even if 
         direct gene is undruggable
```

### Step 5: Drug Matching
```
Sources (in priority order):
  1. ChEMBL API (MCP connected) — bioactivity data
  2. DGIdb REST API — curated drug-gene interactions
  3. ClinicalTrials.gov API — active trials only

Query logic:
  Match driver gene → known drug interactions
  Filter: approved drugs first, then clinical stage
  Exclude: preclinical only (insufficient evidence)
```

### Step 6: Toxicity Pre-filter
```
Tool:    pkCSM REST API
Input:   Drug SMILES string per matched compound
Output:  ADMET predictions:
         AMES toxicity (mutagenicity)
         hERG inhibition (cardiac risk)
         Hepatotoxicity
         BBB penetration (CNS risk if not CNS target)

Filter:  Any predicted toxic = HIGH RISK flag
         Not discarded — ranked lower with explicit flag
```

### Step 7: Normal Tissue Expression Check
```
Tool:    GTEx REST API
Input:   Target gene
Output:  Expression (TPM) across 54 normal tissue types
Flag:    High expression in critical tissue (heart, brain,
         liver, kidney) = ON-TARGET OFF-TUMOR risk
Value:   This is the primary source of clinical toxicity
         for targeted therapies — explicit flag here
```

### Step 8: Track 2 Ranking
```
Final Score =
  druggability_score (fpocket)
  × trial_evidence_level (approved=1.0, phase3=0.8, phase2=0.5)
  × pathway_centrality (Reactome hub score)
  × (1 - toxicity_risk) (pkCSM composite)
  × (1 - normal_tissue_penalty) (GTEx expression)

Output: Ranked drug-target table
  Columns: gene, mutation, drug, mechanism,
           druggability, evidence_level, pathway,
           toxicity_flags, normal_tissue_risk,
           final_score, risk_flag
```

---

## 8. AlphaFold Integration Summary

| Step | Track | Tool | Mode | Rate Limit |
|---|---|---|---|---|
| Peptide-HLA complex | 1 | AlphaFold3 server | Web API | 20 jobs/day |
| Peptide-HLA fallback | 1 | ColabFold API | REST | Moderate |
| Cross-reactivity structure | 1 | ESMFold | HuggingFace API | Free tier |
| Mutant protein structure | 2 | ESMFold | HuggingFace API | Free tier |
| Pocket detection | 2 | fpocket | Local (on downloaded PDB) | None |

### Rate Limit Management
```
AF3 server 20 jobs/day:
  → Apply only to top-20 neoantigen candidates by IC50
  → Queue remaining for next day or ColabFold fallback
  → Job queue managed in SQLite with status tracking

ESMFold HuggingFace:
  → No hard limit but rate-throttled
  → Retry with exponential backoff
  → Cache all results locally (PDB files on 8TB HDD)
  → Never re-run same sequence — check cache first
```

---

## 9. Module Architecture

### 9.1 Backend (FastAPI)

```
backend/
├── main.py                            # App init, CORS, router mount only
├── routers/
│   ├── input.py                       # File upload, format validation
│   ├── track1.py                      # Neoantigen pipeline endpoints
│   ├── track2.py                      # Drug target pipeline endpoints
│   ├── alphafold.py                   # AlphaFold job queue + status
│   └── results.py                     # Unified ranker + export endpoints
├── engine/
│   ├── variant_processor.py           # VCF parsing, annotation, filtering
│   ├── hla_typer.py                   # OptiType wrapper
│   ├── neoantigen_engine.py           # pVACtools + NetMHCpan orchestration
│   ├── binding_scorer.py              # NetMHCpan result parser + normalizer
│   ├── expression_filter.py           # RNA-seq TPM filter logic
│   ├── immunogenicity_scorer.py       # DeepImmuno wrapper
│   ├── cross_reactivity_engine.py     # BLAST + structural comparison
│   ├── driver_gene_engine.py          # dNdScv R subprocess wrapper
│   ├── structure_engine.py            # ESMFold + AF3 + ColabFold API calls
│   ├── pocket_engine.py               # fpocket wrapper + druggability parser
│   ├── pathway_engine.py              # Reactome API client
│   ├── drug_matcher.py                # ChEMBL + DGIdb query logic
│   ├── toxicity_engine.py             # pkCSM API client
│   ├── gtex_engine.py                 # GTEx API client
│   ├── track1_ranker.py               # Track 1 final scoring formula
│   ├── track2_ranker.py               # Track 2 final scoring formula
│   └── report_engine.py               # PDF export (WeasyPrint)
├── parsers/
│   ├── vcf_parser.py                  # VCF format handler (pyVCF or cyvcf2)
│   ├── rnaseq_parser.py               # TSV expression matrix handler
│   ├── hla_parser.py                  # Pre-typed HLA report parser
│   └── pdb_parser.py                  # PDB structure file handler (BioPython)
├── queue/
│   ├── job_queue.py                   # SQLite-backed async job tracker
│   └── af_queue.py                    # AlphaFold rate-limit aware queue
├── cache/
│   └── structure_cache.py             # PDB file cache lookup (avoid re-runs)
├── models/
│   ├── input_schemas.py               # Pydantic: upload + session models
│   ├── track1_schemas.py              # Pydantic: neoantigen models
│   ├── track2_schemas.py              # Pydantic: drug target models
│   ├── structure_schemas.py           # Pydantic: AlphaFold job + result
│   └── result_schemas.py              # Pydantic: unified ranked output
├── db/
│   ├── database.py                    # SQLite connection
│   ├── session_repository.py          # Analysis session CRUD
│   ├── result_repository.py           # Ranked result storage
│   └── queue_repository.py            # Job queue CRUD
└── utils/
    ├── subprocess_runner.py           # Safe subprocess wrapper (OptiType, fpocket, R)
    ├── api_client.py                  # Shared HTTP client with retry + backoff
    ├── sequence_utils.py              # Peptide manipulation, FASTA helpers
    └── pdf_templates/
        ├── track1_report.html
        ├── track2_report.html
        └── unified_report.html
```

### 9.2 Frontend (Vue 3)

```
frontend/
├── src/
│   ├── main.js
│   ├── router/index.js
│   ├── stores/
│   │   ├── sessionStore.js            # Upload state, session ID
│   │   ├── track1Store.js             # Neoantigen results + selection
│   │   ├── track2Store.js             # Drug target results + selection
│   │   ├── structureStore.js          # AlphaFold job status + PDB data
│   │   └── resultStore.js             # Unified ranked output
│   ├── views/
│   │   ├── InputView.vue              # File upload + parameter config
│   │   ├── PipelineView.vue           # Live progress across all steps
│   │   ├── Track1View.vue             # Neoantigen results table + filters
│   │   ├── Track2View.vue             # Drug target results table + filters
│   │   ├── CandidateDetailView.vue    # Single candidate deep-dive
│   │   ├── StructureView.vue          # 3D structure viewer (3Dmol.js)
│   │   └── ExportView.vue             # Report generation + download
│   ├── components/
│   │   ├── upload/
│   │   │   ├── FileDropZone.vue
│   │   │   ├── FormatValidator.vue    # Client-side format check before upload
│   │   │   └── HLAInput.vue           # Manual HLA allele entry option
│   │   ├── pipeline/
│   │   │   ├── StepProgress.vue       # Per-step status indicator
│   │   │   ├── QueueStatus.vue        # AlphaFold job queue viewer
│   │   │   └── LogViewer.vue          # Live pipeline log stream
│   │   ├── results/
│   │   │   ├── RankedTable.vue        # Sortable, filterable results table
│   │   │   ├── RiskBadge.vue          # Risk level indicator (high/med/low)
│   │   │   ├── EvidenceBadge.vue      # Clinical evidence level chip
│   │   │   ├── ScoreBar.vue           # Composite score visual bar
│   │   │   └── CandidateCard.vue      # Summary card for top candidates
│   │   ├── structure/
│   │   │   ├── MolViewer.vue          # 3Dmol.js wrapper
│   │   │   ├── PocketHighlight.vue    # fpocket binding site overlay
│   │   │   └── StructureCompare.vue   # Wildtype vs mutant side-by-side
│   │   ├── charts/
│   │   │   ├── ScoreDistribution.vue  # Histogram of candidate scores (ECharts)
│   │   │   ├── ExpressionHeatmap.vue  # Gene expression across samples (ECharts)
│   │   │   └── PathwayNetwork.vue     # Reactome pathway graph (D3 or ECharts graph)
│   │   └── shared/
│   │       ├── StatusBadge.vue
│   │       ├── ExportButton.vue
│   │       └── PageHeader.vue
│   └── api/
│       ├── inputApi.js
│       ├── track1Api.js
│       ├── track2Api.js
│       ├── alphaFoldApi.js
│       └── resultApi.js
```

---

## 10. API Contract

### Input
| Method | Endpoint | Input | Output |
|---|---|---|---|
| POST | `/input/upload` | VCF + RNA-seq files + HLA config | Session ID |
| POST | `/input/validate` | Session ID | Format validation report |
| POST | `/input/run` | Session ID + track selection | Job started confirmation |

### Track 1
| Method | Endpoint | Input | Output |
|---|---|---|---|
| GET | `/track1/status/{session_id}` | — | Step-by-step progress |
| GET | `/track1/results/{session_id}` | filters | Ranked neoantigen table |
| GET | `/track1/candidate/{id}` | — | Full candidate detail |

### Track 2
| Method | Endpoint | Input | Output |
|---|---|---|---|
| GET | `/track2/status/{session_id}` | — | Step-by-step progress |
| GET | `/track2/results/{session_id}` | filters | Ranked drug-target table |
| GET | `/track2/candidate/{id}` | — | Full candidate detail |

### AlphaFold Queue
| Method | Endpoint | Input | Output |
|---|---|---|---|
| GET | `/alphafold/queue` | session_id | Queue position, ETA |
| GET | `/alphafold/job/{job_id}` | — | Job status + PDB download link |

### Results
| Method | Endpoint | Input | Output |
|---|---|---|---|
| GET | `/results/unified/{session_id}` | — | Combined ranked output |
| GET | `/results/export/{session_id}` | format: pdf/json | Report binary |

---

## 11. Key Data Models

### Neoantigen Candidate
```
NeoantigenCandidate:
  id: UUID
  session_id: UUID
  peptide_sequence: str
  source_gene: str
  mutation: str               (e.g. KRAS_G12D)
  mutation_type: str          (missense/frameshift/splice)
  hla_allele: str
  ic50_nm: float
  percentile_rank: float
  af3_plddt: float | null
  sasa_exposed_percent: float | null
  tpm_expression: float
  immunogenicity_score: float
  cross_reactivity_risk: float
  cross_reactivity_flag: str  (low/moderate/high)
  final_score: float
  risk_flags: List[str]
```

### Drug Target Candidate
```
DrugTargetCandidate:
  id: UUID
  session_id: UUID
  gene: str
  mutation: str
  dndsv_q_value: float
  druggability_score: float
  pocket_volume: float | null
  drug_name: str
  drug_smiles: str
  mechanism: str
  evidence_level: str         (approved/phase3/phase2/preclinical)
  pathway: str
  toxicity_flags: List[str]   (AMES/hERG/hepatotoxic)
  normal_tissue_risk: str     (low/moderate/high)
  gtex_max_expression_tissue: str
  final_score: float
  risk_flags: List[str]
```

---

## 12. Scoring Logic (Explicit Formulas)

### Track 1 — Neoantigen Final Score
```python
def score_neoantigen(candidate):
    # Normalize IC50: 0nM = 1.0, 500nM = 0.5, 5000nM = 0.0
    binding = max(0, 1 - (candidate.ic50_nm / 5000))

    # AlphaFold pLDDT: 90+ = confident, <50 = poor
    structure = (candidate.af3_plddt / 90) if candidate.af3_plddt else 0.5

    # SASA: % of peptide residues exposed to TCR
    exposure = candidate.sasa_exposed_percent / 100 if candidate.sasa_exposed_percent else 0.5

    # Immunogenicity: 0–1 direct
    immuno = candidate.immunogenicity_score

    # Expression: TPM normalized, cap at 100
    expression = min(candidate.tpm_expression / 100, 1.0)

    # Cross-reactivity penalty
    cr_penalty = {"low": 0.0, "moderate": 0.3, "high": 0.8}
    cr = cr_penalty[candidate.cross_reactivity_flag]

    final = (
        (binding * 0.25) +
        (structure * 0.20) +
        (exposure * 0.15) +
        (immuno * 0.20) +
        (expression * 0.20)
    ) * (1 - cr)

    return round(final, 4)
```

### Track 2 — Drug Target Final Score
```python
def score_drug_target(candidate):
    # Druggability: fpocket score 0–1
    drug = candidate.druggability_score

    # Evidence: approved=1.0, phase3=0.8, phase2=0.5, preclinical=0.2
    evidence_map = {"approved": 1.0, "phase3": 0.8,
                    "phase2": 0.5, "preclinical": 0.2}
    evidence = evidence_map.get(candidate.evidence_level, 0.1)

    # Toxicity: count of flags, each flag = 0.2 penalty
    tox_penalty = min(len(candidate.toxicity_flags) * 0.2, 0.8)

    # Normal tissue risk
    tissue_penalty = {"low": 0.0, "moderate": 0.2, "high": 0.5}
    tissue = tissue_penalty[candidate.normal_tissue_risk]

    final = (
        (drug * 0.35) +
        (evidence * 0.35)
    ) * (1 - tox_penalty) * (1 - tissue)

    return round(final, 4)
```

---

## 13. UI Design

- **Layout:** Left nav sidebar (track/step selector), right content area
- **Color:** Dark sidebar. Track 1 accent: teal (#00897B). Track 2 accent: indigo (#3949AB). Risk: red (#E53935). Pass: green (#43A047)
- **Structure viewer:** 3Dmol.js embedded in CandidateDetailView — no external server
- **Pipeline progress:** Step-by-step status with estimated time remaining per step
- **Results table:** Sortable by any column, filter by risk flag, score threshold slider
- **No modals:** All detail views are routed pages, not overlays
- **Disclaimer banner:** Persistent on all result views — "Research grade output only. Not for clinical use."

---

## 14. Build Phases

### Phase 1 — Input + Variant Processor (Days 1–2)
- `parsers/vcf_parser.py` (cyvcf2)
- `parsers/rnaseq_parser.py`
- `parsers/hla_parser.py`
- `engine/variant_processor.py` (Ensembl VEP annotation via API)
- `models/input_schemas.py`
- `db/database.py` + `db/session_repository.py`
- `routers/input.py`
- `queue/job_queue.py`
- Validate: upload Sid's VCF → annotated variant list returned

### Phase 2 — Track 1 Core (Days 3–5)
- `engine/hla_typer.py` (OptiType subprocess)
- `engine/neoantigen_engine.py` (pVACtools subprocess)
- `engine/binding_scorer.py` (NetMHCpan subprocess + parser)
- `engine/expression_filter.py`
- `models/track1_schemas.py`
- `db/result_repository.py`
- `routers/track1.py`
- Validate: Sid's VCF + RNA-seq → neoantigen candidate list with IC50

### Phase 3 — AlphaFold Integration (Days 6–7)
- `engine/structure_engine.py` (ESMFold + AF3 + ColabFold)
- `cache/structure_cache.py`
- `queue/af_queue.py` (rate-limit aware, SQLite backed)
- `parsers/pdb_parser.py` (BioPython SASA calculation)
- `routers/alphafold.py`
- Validate: top-5 neoantigen candidates → PDB files downloaded, SASA calculated

### Phase 4 — Track 1 Complete (Day 8)
- `engine/immunogenicity_scorer.py` (DeepImmuno local)
- `engine/cross_reactivity_engine.py` (BLAST + ESMFold structure compare)
- `engine/track1_ranker.py` (scoring formula)
- Validate: full Track 1 score table for Sid's data

### Phase 5 — Track 2 Core (Days 9–10)
- `engine/driver_gene_engine.py` (dNdScv R subprocess)
- `engine/pocket_engine.py` (fpocket on ESMFold-predicted PDB)
- `engine/pathway_engine.py` (Reactome API)
- `engine/drug_matcher.py` (ChEMBL MCP + DGIdb REST)
- `engine/toxicity_engine.py` (pkCSM API)
- `engine/gtex_engine.py` (GTEx API)
- `engine/track2_ranker.py`
- `models/track2_schemas.py`
- `routers/track2.py`
- Validate: Sid's VCF → driver genes → drug matches with toxicity flags

### Phase 6 — Frontend Core (Days 11–13)
- Vue 3 + Vite scaffold, Pinia, Vue Router
- `InputView.vue` + upload components
- `PipelineView.vue` + `StepProgress.vue` + `QueueStatus.vue`
- `Track1View.vue` + `RankedTable.vue`
- `Track2View.vue` + `RankedTable.vue`
- `CandidateDetailView.vue`
- All API modules wired

### Phase 7 — Structure Viewer + Charts (Days 14–15)
- `StructureView.vue` (3Dmol.js)
- `StructureCompare.vue` (wildtype vs mutant)
- `PocketHighlight.vue`
- `ScoreDistribution.vue` (ECharts)
- `ExpressionHeatmap.vue` (ECharts)
- `PathwayNetwork.vue` (ECharts graph)

### Phase 8 — Export + Polish (Day 16)
- `engine/report_engine.py` (WeasyPrint PDF)
- PDF templates for Track 1, Track 2, unified
- Disclaimer banner on all result views
- README + architecture diagram
- Sample data subset from Sid's dataset committed to `/data`

---

## 15. Constraints and Assumptions

| Constraint | Detail |
|---|---|
| Input VCF | Assumes somatic-only VCF (germline subtracted). Pipeline does not run GATK somatic calling — too compute-heavy for local |
| AlphaFold rate limit | AF3 server: 20 jobs/day. Top-N candidates queued, remainder use ColabFold or ESMFold |
| GTX1650 4GB VRAM | DeepImmuno local — marginal fit. If OOM, falls back to IEDB API |
| NetMHCpan | Requires license acceptance for download. User must install manually — documented in setup |
| pVACtools | Python 3.8 dependency conflict possible with FastAPI (3.10+). Run in isolated venv |
| Cross-reactivity | BLAST against human proteome requires local BLAST+ install + human proteome FASTA download (~1GB) |
| Output framing | All result views must display: "Research grade output. Not for clinical use." — non-removable |
| Sid's data | Download selectively from GCS bucket — VCF + RNA-seq TSV only in v1. BAM for HLA if needed |
| dNdScv | R dependency — user must have R installed. Subprocess call with timeout |

---

## 16. README Positioning (Draft)

```
An open-source precision oncology pipeline for neoantigen 
prediction and drug target identification from patient 
genomic data. Accepts somatic VCF + RNA-seq input, runs 
binding affinity prediction, AlphaFold structural validation, 
immunogenicity scoring, cross-reactivity filtering, and 
drug-target toxicity assessment — producing ranked therapeutic 
hypotheses with explicit evidence levels and risk flags.

Built on Sid Sijbrandij's public osteosarcoma dataset.
Research grade. Not for clinical use.
```

---

## 17. Future Scope (Post v1)

- Raw FASTQ support (GATK somatic calling pipeline — requires cloud compute)
- scRNA-seq cell-type deconvolution integrated into expression filter
- Multi-patient cohort comparison
- Personalized vaccine sequence design output (peptide → mRNA sequence)
- CAR-T target surface expression filter (membrane protein check)
- Cloud deployment with GPU instance for local AlphaFold2
- ClinVar + COSMIC database cross-reference
- Survival correlation (TCGA survival data vs gene expression)
- Interactive pathway editing (user can remove/add pathway nodes)
- AlphaFold3 local when GPU upgraded (minimum RTX 3090 24GB)
