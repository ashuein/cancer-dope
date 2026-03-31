# PrecisionOncology Pipeline

> **Status: Planning stage.** Architecture and task list are defined. Implementation has not started. The structure, commands, and endpoints described below represent the planned design, not the current state of the repository.

An open-source precision oncology pipeline for neoantigen prediction and drug target identification from patient genomic data.

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Vue 3](https://img.shields.io/badge/Vue-3-brightgreen.svg)](https://vuejs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue.svg)](https://typescriptlang.org)
[![Research Grade](https://img.shields.io/badge/Output-Research%20Grade-orange.svg)](#disclaimer)

> **Research grade output only. Not for clinical use.**

---

## What It Does

Accepts somatic VCF and RNA-seq input, runs binding affinity prediction, AlphaFold structural validation, immunogenicity scoring, cross-reactivity filtering, and drug-target toxicity assessment. Produces ranked therapeutic hypotheses with explicit evidence levels and risk flags.

Built on [Sid Sijbrandij's public osteosarcoma dataset](https://osteosarc.com).

---

## Features

### Track 1 --- Neoantigen Pipeline
- HLA typing from BAM (OptiType) or manual input
- Neoantigen candidate generation (pVACtools)
- MHC binding affinity prediction (NetMHCpan 4.1)
- AlphaFold3 structural validation of peptide-HLA binding
- Solvent-accessible surface area analysis (TCR exposure)
- Expression filtering from RNA-seq (TPM threshold)
- Immunogenicity scoring (DeepImmuno / IEDB)
- Cross-reactivity check (BLAST + structural comparison)
- Composite ranking with per-candidate risk flags

### Track 2 --- Drug Target Pipeline
- Driver gene identification (dNdScv)
- Mutant protein structure prediction (ESMFold)
- Binding pocket detection and druggability scoring (fpocket)
- Pathway mapping (Reactome)
- Drug matching (ChEMBL + DGIdb)
- ADMET toxicity pre-filtering (pkCSM)
- Normal tissue expression check (GTEx)
- Composite ranking with toxicity and off-target flags

---

## Architecture Overview

```
Browser (Vue 3 + TypeScript)
    |
    v
FastAPI Backend (Python 3.11, host process — not containerized)
    |
    +---> Variant Processor (VCF parsing + VEP annotation)
    |         |
    |         +---> Track 1: Neoantigen Pipeline
    |         |       HLA -> pVACtools [container] -> NetMHCpan -> AlphaFold
    |         |       -> Immunogenicity -> Cross-reactivity -> Ranker
    |         |
    |         +---> Track 2: Drug Target Pipeline
    |                 dNdScv [container] -> ESMFold -> fpocket [container]
    |                 -> Reactome -> ChEMBL/DGIdb -> pkCSM -> GTEx -> Ranker
    |
    +---> SQLite (host filesystem)
    +---> Structure Cache (PDB files on disk)
    +---> Docker Compose (tool containers: pVACtools, BLAST, fpocket, R)
    +---> External APIs (AlphaFold3, ESMFold, Reactome, ChEMBL, etc.)
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker Desktop | Latest | Required for backend containers |
| Node.js | 20 LTS | Frontend dev server |
| Git | 2.x+ | Version control |
| NetMHCpan 4.1 | 4.1 | Manual download, academic license required |

See [docs/dependency-setup-guide.md](docs/dependency-setup-guide.md) for detailed installation instructions.

---

## Quick Start (Planned)

> These commands will work once Phase 0 scaffolding is complete. See [docs/task-list.md](docs/task-list.md) for current progress.

```bash
# 1. Clone the repository
git clone https://github.com/your-org/cancer-drug-pipeline.git
cd cancer-drug-pipeline

# 2. Copy environment config
cp .env.example .env
# Edit .env with your API tokens (HuggingFace, AlphaFold server)

# 3. Start tool containers (pVACtools, BLAST, fpocket, R)
docker compose up -d

# 4. Start backend (host process)
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 5. Start frontend dev server (new terminal)
cd frontend
npm install
npm run dev

# 6. Open browser
# Navigate to http://localhost:5173
```

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Vue 3 + TypeScript + Vite | Single-page application |
| State Management | Pinia | Reactive stores |
| Charts | ECharts | Score distributions, heatmaps, pathway graphs |
| 3D Viewer | 3Dmol.js | Protein structure visualization |
| Backend | FastAPI (Python 3.11) | REST API + WebSocket |
| Database | SQLite (WAL mode) | Sessions, results, job queue |
| PDF Export | WeasyPrint | Report generation |
| Containers | Docker Compose | Service orchestration |

### Bioinformatics Tools
| Tool | Purpose | Execution |
|---|---|---|
| OptiType | HLA typing | Docker container |
| pVACtools | Neoantigen generation | Isolated container (Python 3.8) |
| NetMHCpan 4.1 | MHC binding prediction | Local binary (academic license) |
| BLAST+ | Cross-reactivity screening | Docker container |
| fpocket | Binding pocket detection | Docker container |
| dNdScv | Driver gene identification | R subprocess |
| DeepImmuno | Immunogenicity scoring | Local GPU (GTX1650) |

### External APIs
> API availability is a current assumption, not a guarantee. Each integration includes retry logic and fallback behavior. See [docs/architecture-assessment.md](docs/architecture-assessment.md) for risk analysis.

| Service | Purpose | Availability (as of v1 design) |
|---|---|---|
| AlphaFold3 Server | Peptide-HLA complex prediction | 20 jobs/day (free tier) |
| ESMFold (HuggingFace) | Fast monomer structure prediction | Free tier, rate-throttled |
| ColabFold | AlphaFold2 fallback | Public, rate-limited |
| Reactome | Pathway mapping | Public REST, no auth required |
| ChEMBL | Drug bioactivity data | Public REST, no auth required |
| DGIdb | Drug-gene interactions | Public REST, no auth required |
| pkCSM | ADMET toxicity prediction | Public REST, no auth required |
| GTEx | Normal tissue expression | Public REST, no auth required |

---

## Planned API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/input/upload` | Upload VCF + RNA-seq + HLA config |
| POST | `/input/validate` | Validate uploaded file formats |
| POST | `/input/run` | Start pipeline execution |
| GET | `/track1/status/{id}` | Track 1 step-by-step progress |
| GET | `/track1/results/{id}` | Ranked neoantigen table |
| GET | `/track1/candidate/{id}` | Full candidate detail |
| GET | `/track2/status/{id}` | Track 2 step-by-step progress |
| GET | `/track2/results/{id}` | Ranked drug-target table |
| GET | `/track2/candidate/{id}` | Full candidate detail |
| GET | `/alphafold/queue` | AlphaFold job queue status |
| GET | `/results/unified/{id}` | Combined ranked output |
| GET | `/results/export/{id}` | PDF/JSON report download |
| GET | `/health` | Service health check |
| WS | `/ws/pipeline/{id}` | Real-time pipeline progress |

---

## Planned Project Structure

> This is the target directory layout. Only `docs/`, `README.md`, `LICENSE`, and `.gitignore` exist currently. Remaining directories and files are created during Phase 0 scaffolding.

```
cancer-drug-pipeline/
+-- backend/
|   +-- main.py
|   +-- routers/          # API endpoints
|   +-- engine/           # Pipeline logic (track1/, track2/)
|   +-- parsers/          # VCF, RNA-seq, HLA, PDB parsers
|   +-- models/           # Pydantic schemas
|   +-- db/               # SQLite + repositories
|   +-- queue/            # Job queue + AlphaFold rate limiter
|   +-- cache/            # Structure file cache
|   +-- config/           # Settings (pydantic-settings)
|   +-- middleware/       # Error handling, logging
|   +-- tests/            # pytest unit + integration tests
+-- frontend/
|   +-- src/
|       +-- views/        # Page components
|       +-- components/   # Reusable UI components
|       +-- stores/       # Pinia state management
|       +-- api/          # Backend API client modules
|       +-- types/        # TypeScript interfaces
+-- docker/               # Per-service Dockerfiles
+-- docs/                 # Architecture, setup, task list
+-- data/                 # Sample data (gitignored)
+-- scripts/              # Dev and build scripts
+-- .env.example
+-- docker-compose.yml
+-- README.md
+-- LICENSE
```

---

## Documentation

- [Project Plan v1](docs/precision-oncology-pipeline-plan-v1.md) --- Full specification
- [Architecture Assessment](docs/architecture-assessment.md) --- Risk analysis and improvements
- [Architecture Diagrams](docs/architecture-diagram.md) --- System and data flow diagrams
- [Dependency Setup Guide](docs/dependency-setup-guide.md) --- Installation instructions
- [Task List](docs/task-list.md) --- Implementation checklist

---

## Contributing

Contributions are welcome. Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes with clear messages
4. Push to your branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please ensure your code passes linting (`ruff check` for Python, `eslint` for TypeScript) and includes tests for new functionality.

---

## License

This project is licensed under the **GNU Affero General Public License v3.0** --- see [LICENSE](LICENSE) for details.

**Third-party licenses:** This pipeline integrates with tools that have independent licensing requirements. In particular, NetMHCpan 4.1 requires a separate academic license from [DTU Health Tech](https://services.healthtech.dtu.dk/services/NetMHCpan-4.1/). Users must obtain and comply with all third-party licenses independently.

---

## Acknowledgments

- **Reference Dataset:** [Sid Sijbrandij Osteosarcoma](https://osteosarc.com) public genomic data
- **Bioinformatics Tools:** OptiType, pVACtools, NetMHCpan, BLAST+, fpocket, dNdScv, DeepImmuno
- **Structure Prediction:** AlphaFold3 (DeepMind), ESMFold (Meta), ColabFold
- **Data Sources:** Reactome, ChEMBL, DGIdb, GTEx, pkCSM, Ensembl VEP

---

## Disclaimer

This software produces **research-grade output only**. It is **not intended for clinical use**, medical diagnosis, or treatment decisions. All results are computational predictions that require experimental validation. The developers assume no responsibility for decisions made based on this software's output.

Always consult qualified medical professionals for clinical decisions.
