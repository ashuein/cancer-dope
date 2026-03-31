# Dependency Setup Guide --- PrecisionOncology Pipeline

**Date:** March 31, 2026
**Target OS:** Windows 11 / Linux / macOS (Docker-based)

> **Note:** This document describes the planned environment design. The Docker Compose files, Dockerfiles, `.env.example`, and scripts referenced below do not exist yet --- they are created during Phase 0 scaffolding (see [task-list.md](task-list.md)). Treat this as a specification for what will be built, not instructions to run today.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Docker Setup](#2-docker-setup)
3. [Backend Dependencies](#3-backend-dependencies)
4. [pVACtools Isolated Container](#4-pvactools-isolated-container)
5. [Bioinformatics Tools](#5-bioinformatics-tools)
6. [Frontend Dependencies](#6-frontend-dependencies)
7. [External API Accounts](#7-external-api-accounts)
8. [Data Downloads](#8-data-downloads)
9. [Environment Variables](#9-environment-variables)
10. [Verification](#10-verification)

---

## 1. Prerequisites

| Requirement | Version | Download |
|---|---|---|
| Docker Desktop | Latest | https://www.docker.com/products/docker-desktop/ |
| Node.js | 20 LTS | https://nodejs.org/ (or via nvm) |
| Git | 2.x+ | https://git-scm.com/ |
| GPU drivers (optional) | Latest | NVIDIA drivers for DeepImmuno GPU acceleration |

### Windows-Specific
- Docker Desktop requires WSL2 backend (auto-configured on Windows 11)
- Ensure "Use the WSL 2 based engine" is checked in Docker Desktop settings
- Allocate at least 8GB RAM to Docker in Settings > Resources

### Linux-Specific
- Install Docker Engine + Docker Compose plugin
- Add your user to the `docker` group: `sudo usermod -aG docker $USER`

---

## 2. Docker Setup

### 2.1 Docker Compose Overview

The project uses 5 Docker services:

| Service | Base Image | Purpose |
|---|---|---|
| `app` | `python:3.11-slim` | FastAPI backend, pipeline orchestrator |
| `pvactools` | `python:3.8-slim` | pVACtools neoantigen generation (isolated) |
| `blast` | `ncbi/blast:latest` | BLAST+ for cross-reactivity screening |
| `fpocket` | `ubuntu:22.04` | fpocket binding pocket detection |
| `r-engine` | `r-base:4.3` | R + dNdScv for driver gene identification |

### 2.2 Build and Start (after Phase 0 scaffolding is complete)

```bash
# Clone the repository
git clone https://github.com/your-org/cancer-drug-pipeline.git
cd cancer-drug-pipeline

# Copy environment config
cp .env.example .env
# Edit .env with your API tokens

# Build all containers
docker compose build

# Start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f app
```

### 2.3 Docker Resource Recommendations

```
Docker Desktop Settings > Resources:
  CPUs:    6+ (for parallel tool execution)
  Memory:  12 GB minimum (16 GB recommended)
  Swap:    4 GB
  Disk:    100 GB+ (structure cache, BLAST DB)
```

### 2.4 Volume Structure

```
pipeline-data volume:
  /data/
  +-- uploads/         Uploaded VCF, RNA-seq, HLA files
  +-- intermediate/    Step outputs (annotated VCF, peptide lists)
  +-- results/         Final ranked tables, scores
  +-- cache/           PDB structure file cache
  +-- blast-db/        Human proteome BLAST database

blast-db volume:
  /blast-db/           Pre-built BLAST database files
```

---

## 3. Backend Dependencies (app container)

### 3.1 Python 3.11 Packages

The `app` container installs these via `requirements.txt`:

**Core Framework:**
```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
```

**Database:**
```
sqlalchemy>=2.0.25
aiosqlite>=0.19.0
alembic>=1.13.0
```

**Bioinformatics:**
```
biopython>=1.83
cyvcf2>=0.31.0
pandas>=2.2.0
numpy>=1.26.0
scipy>=1.12.0
```

**HTTP + WebSocket:**
```
httpx>=0.26.0
websockets>=12.0
```

**PDF Export:**
```
weasyprint>=61.0
jinja2>=3.1.3
```

**Utilities:**
```
python-multipart>=0.0.6
aiofiles>=23.2.0
python-dotenv>=1.0.0
```

**Development:**
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
ruff>=0.2.0
mypy>=1.8.0
```

### 3.2 Dockerfile (docker/app.Dockerfile)

```dockerfile
FROM python:3.11-slim

# System dependencies for cyvcf2, weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libhts-dev \
    zlib1g-dev \
    libbz2-dev \
    liblzma-dev \
    libcurl4-openssl-dev \
    libffi-dev \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4. pVACtools Isolated Container

### Why Isolated?
pVACtools requires Python 3.8 and has dependency conflicts with FastAPI (Python 3.10+). It runs in its own container.

### Communication Pattern
The `app` container communicates with `pvactools` via HTTP sidecar:
- pVACtools container runs a thin Flask API on port 8001
- `app` sends POST requests with VCF path + HLA alleles
- pVACtools writes output to shared volume `/data/intermediate/`

### Dockerfile (docker/pvactools.Dockerfile)

```dockerfile
FROM python:3.8-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pvactools \
    flask \
    gunicorn

WORKDIR /app
COPY pvactools_sidecar.py .

EXPOSE 8001
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8001", "pvactools_sidecar:app"]
```

---

## 5. Bioinformatics Tools

### 5.1 OptiType (HLA Typing)

**Installed in:** `app` container (Python 3.11 compatible)
```bash
pip install optitype
# OR install via conda in the container
```

**Alternative:** If OptiType has Python version issues, run via subprocess in a dedicated container similar to pVACtools.

**Test:**
```bash
docker compose exec app python -c "import optitype; print('OptiType OK')"
```

### 5.2 NetMHCpan 4.1 (Binding Affinity)

**MANUAL INSTALL REQUIRED** --- Academic license only.

1. Go to https://services.healthtech.dtu.dk/services/NetMHCpan-4.1/
2. Request academic license (requires institutional email)
3. Download the Linux tarball
4. Extract to a known location (e.g., `./tools/netMHCpan-4.1/`)
5. Mount into the `app` container via docker-compose volume:
   ```yaml
   volumes:
     - ./tools/netMHCpan-4.1:/opt/netMHCpan-4.1
   ```
6. Set environment variable: `NETMHCPAN_PATH=/opt/netMHCpan-4.1/Linux_x86_64/bin/netMHCpan`

**Test:**
```bash
docker compose exec app /opt/netMHCpan-4.1/Linux_x86_64/bin/netMHCpan -h
```

### 5.3 BLAST+ (Cross-Reactivity)

**Installed in:** `blast` container (official NCBI image)

The `blast` container uses the official `ncbi/blast:latest` image. Human proteome BLAST database is pre-built in the `blast-db` volume.

**Initial database setup (one-time):**
```bash
# Download human proteome
docker compose exec blast wget -O /blast-db/human_proteome.fasta \
  "https://rest.uniprot.org/uniprotkb/stream?format=fasta&query=(organism_id:9606)+AND+(reviewed:true)"

# Build BLAST database
docker compose exec blast makeblastdb \
  -in /blast-db/human_proteome.fasta \
  -dbtype prot \
  -out /blast-db/human_proteome \
  -title "Human Proteome (UniProt reviewed)"
```

**Test:**
```bash
docker compose exec blast blastp -version
```

### 5.4 fpocket (Pocket Detection)

**Installed in:** `fpocket` container

### Dockerfile (docker/fpocket.Dockerfile)

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libnetcdf-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/Discngine/fpocket.git /opt/fpocket \
    && cd /opt/fpocket \
    && make \
    && make install

ENTRYPOINT ["tail", "-f", "/dev/null"]
```

**Test:**
```bash
docker compose exec fpocket fpocket -h
```

### 5.5 dNdScv (Driver Gene Identification)

**Installed in:** `r-engine` container

### Dockerfile (docker/r-engine.Dockerfile)

```dockerfile
FROM r-base:4.3

RUN R -e "install.packages('BiocManager', repos='https://cloud.r-project.org')" \
    && R -e "BiocManager::install('dndscv')" \
    && R -e "library(dndscv); cat('dNdScv installed successfully\n')"

ENTRYPOINT ["tail", "-f", "/dev/null"]
```

**Test:**
```bash
docker compose exec r-engine R -e "library(dndscv); cat('OK\n')"
```

### 5.6 DeepImmuno (Immunogenicity Scoring)

**Installed in:** `app` container
**Requires:** NVIDIA GPU (GTX 1650, 4GB VRAM) --- optional

```bash
pip install deepimmuno
```

**GPU Setup (optional):**
- Install NVIDIA Container Toolkit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/
- Add to docker-compose.yml for `app` service:
  ```yaml
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  ```

**Fallback:** If GPU unavailable or OOM, pipeline automatically falls back to IEDB Immunogenicity API.

---

## 6. Frontend Dependencies

### 6.1 Setup

```bash
# Install Node.js 20 LTS (via nvm recommended)
nvm install 20
nvm use 20

# Create Vue 3 + TypeScript project
cd frontend
npm install

# Start dev server
npm run dev
# Opens at http://localhost:5173
```

### 6.2 Package Dependencies

**package.json dependencies:**
```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.3.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "echarts": "^5.5.0",
    "vue-echarts": "^6.6.0",
    "3dmol": "^2.1.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.1.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "vitest": "^1.3.0",
    "@vue/test-utils": "^2.4.0",
    "eslint": "^8.56.0",
    "@typescript-eslint/eslint-plugin": "^7.0.0",
    "prettier": "^3.2.0",
    "tailwindcss": "^3.4.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

### 6.3 Vite Configuration

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

---

## 7. External API Accounts

### Required Accounts

| Service | Registration | Token/Key | Free Tier |
|---|---|---|---|
| AlphaFold3 Server | https://alphafoldserver.com | Account login | 20 jobs/day |
| HuggingFace | https://huggingface.co/settings/tokens | API token | Free for ESMFold inference |

### No Account Needed

These APIs are publicly accessible without authentication:

| Service | Base URL |
|---|---|
| Reactome | https://reactome.org/ContentService |
| ChEMBL | https://www.ebi.ac.uk/chembl/api/data |
| DGIdb | https://dgidb.org/api |
| GTEx | https://gtexportal.org/api/v2 |
| pkCSM | https://biosig.lab.uq.edu.au/pkcsm |
| Ensembl VEP | https://rest.ensembl.org |
| IEDB | http://tools-cluster-interface.iedb.org/tools_api |

---

## 8. Data Downloads

### 8.1 Human Proteome (Required for BLAST)

```bash
# Download UniProt reviewed human proteome (~1 GB)
wget -O data/human_proteome.fasta \
  "https://rest.uniprot.org/uniprotkb/stream?format=fasta&query=(organism_id:9606)+AND+(reviewed:true)"

# Build BLAST database (run inside blast container)
docker compose exec blast makeblastdb \
  -in /data/blast-db/human_proteome.fasta \
  -dbtype prot \
  -out /data/blast-db/human_proteome
```

### 8.2 Sample Data (Sid Sijbrandij Osteosarcoma)

Selective download from GCS bucket `osteosarc-genomics`:

```bash
# Install gsutil if not available
pip install gsutil

# Download somatic VCF (~2 GB)
gsutil cp gs://osteosarc-genomics/vcf/somatic_variants.vcf.gz data/

# Download RNA-seq processed TSV (~50 GB)
gsutil cp gs://osteosarc-genomics/rnaseq/expression_matrix.tsv data/

# Download HLA typing report (if available)
gsutil cp gs://osteosarc-genomics/hla/hla_typing_report.txt data/
```

**Do NOT download:**
- Raw FASTQ files (multi-TB each)
- Full WGS BAM set (15TB+)

### 8.3 Test Fixtures (Bundled)

Small sample files for testing are included in `tests/fixtures/`:
- `sample.vcf` --- 10 somatic variants
- `sample_expression.tsv` --- 100 genes with TPM values
- `sample_hla.txt` --- Pre-typed HLA alleles (HLA-A*02:01, etc.)

---

## 9. Environment Variables

### .env.example

```bash
# ============ API Configuration ============
# AlphaFold3 server credentials
AF3_SERVER_URL=https://alphafoldserver.com/api
AF3_DAILY_LIMIT=20

# HuggingFace (ESMFold inference)
HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
ESMFOLD_API_URL=https://api-inference.huggingface.co/models/facebook/esmfold_v1

# ColabFold (AF2 fallback)
COLABFOLD_API_URL=https://api.colabfold.com

# Bioinformatics APIs
REACTOME_BASE_URL=https://reactome.org/ContentService
CHEMBL_BASE_URL=https://www.ebi.ac.uk/chembl/api/data
DGIDB_BASE_URL=https://dgidb.org/api
GTEX_BASE_URL=https://gtexportal.org/api/v2
PKCSM_BASE_URL=https://biosig.lab.uq.edu.au/pkcsm
VEP_BASE_URL=https://rest.ensembl.org
IEDB_BASE_URL=http://tools-cluster-interface.iedb.org/tools_api

# ============ Local Tool Paths ============
NETMHCPAN_PATH=/opt/netMHCpan-4.1/Linux_x86_64/bin/netMHCpan

# ============ Database ============
DATABASE_URL=sqlite+aiosqlite:///./pipeline.db

# ============ File Paths ============
UPLOAD_DIR=/data/uploads
INTERMEDIATE_DIR=/data/intermediate
RESULTS_DIR=/data/results
CACHE_DIR=/data/cache
BLAST_DB_PATH=/data/blast-db/human_proteome

# ============ Application ============
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
DEBUG=false
```

---

## 10. Verification

### 10.1 Verify Docker Services

```bash
# All 5 services should be running
docker compose ps

# Expected output:
# NAME         STATUS
# app          running (healthy)
# pvactools    running
# blast        running
# fpocket      running
# r-engine     running
```

### 10.2 Verify Individual Tools

```bash
# FastAPI health check
curl http://localhost:8000/health

# NetMHCpan
docker compose exec app $NETMHCPAN_PATH -h

# BLAST
docker compose exec blast blastp -version

# fpocket
docker compose exec fpocket fpocket -h

# R + dNdScv
docker compose exec r-engine R -e "library(dndscv); cat('OK\n')"

# pVACtools sidecar
curl http://localhost:8001/health
```

### 10.3 Verify Frontend

```bash
cd frontend
npm run dev
# Open http://localhost:5173 --- should see the application
npm run type-check  # TypeScript validation
npm run lint        # ESLint check
npm run test        # Vitest unit tests
```

### 10.4 Verification Script

A convenience script `scripts/verify-setup.sh` checks all dependencies:

```bash
chmod +x scripts/verify-setup.sh
./scripts/verify-setup.sh

# Expected output:
# [PASS] Docker Engine running
# [PASS] app container healthy
# [PASS] pvactools container healthy
# [PASS] blast container running
# [PASS] fpocket container running
# [PASS] r-engine container running
# [PASS] NetMHCpan accessible
# [PASS] BLAST database built
# [PASS] Node.js 20.x installed
# [PASS] Frontend dependencies installed
# [WARN] HuggingFace API token not set (ESMFold will fail)
# [INFO] All critical checks passed
```
