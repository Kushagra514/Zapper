# Deployment Guide

> **Date:** 2026-10-10  
> **Target OS:** Ubuntu 22.04 LTS / Debian 12 (Linux)  
> **Python:** 3.11+

---

## 1. Quick Start (Local Development)

### 1.1 Prerequisites

```bash
# System packages
sudo apt-get update
sudo apt-get install -y \
    python3.11 python3.11-venv \
    redis-server \
    libgomp1 libgl1 libglib2.0-0 \  # PaddleOCR dependencies
    git curl

# uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# (Optional) Ollama for local AI inference
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &
ollama pull llama3.2-vision:11b   # ~8 GB download
```

### 1.2 Project Setup

```bash
# Clone / navigate to project
cd "/home/kushagra/Downloads/MECH AI ADDON"

# Create virtual environment and install dependencies
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env — add API keys if using cloud providers
```

### 1.3 Configuration (`.env`)

```bash
# AI Providers — set only what you use
OPENAI_API_KEY=                         # GPT-4o (optional)
GOOGLE_API_KEY=                         # Gemini (optional; free tier available)
ANTHROPIC_API_KEY=                      # Claude (optional)
OLLAMA_BASE_URL=http://localhost:11434  # Local Ollama (default)

# Default model config — use local Ollama if no cloud key
DEFAULT_VISION_PROVIDER=ollama
DEFAULT_VISION_MODEL=llama3.2-vision:11b

# Database
DATABASE_URL=sqlite:///./data/mech_cad.db

# Artifact storage (local filesystem)
ARTIFACT_STORE_PATH=./data/artifacts
ARTIFACT_STORE_BACKEND=local

# Redis (for job queue)
REDIS_URL=redis://localhost:6379/0

# API security
AUTH_DISABLED=true                      # Set false for production
API_SECRET_KEY=dev-secret-change-this

# Logging
LOG_LEVEL=INFO
```

### 1.4 Initialize Database

```bash
# Create database schema
python -m mech_cad db upgrade

# Verify
python -m mech_cad db status
```

### 1.5 Start Services

**Terminal 1 — API server:**
```bash
uvicorn mech_cad.api.main:app --reload --port 8000
```

**Terminal 2 — Job worker:**
```bash
rq worker mech-cad-jobs --url redis://localhost:6379/0
```

**Terminal 3 — Redis (if not already running as service):**
```bash
redis-server
```

Open: `http://localhost:8000` (web UI) or `http://localhost:8000/docs` (OpenAPI).

---

## 2. Verifying the Installation

```bash
# Run unit tests (no API keys required)
python -m pytest tests/unit/ -v

# Run a minimal integration smoke test
python -m pytest tests/integration/test_pipeline_simple.py -v \
    --use-local-model   # Uses Ollama if available, else skips VLM stages

# Check a benchmark case (requires Ollama or cloud API key)
python -m mech_cad benchmark run --case A001 --config configs/default.yaml
```

Expected smoke-test output:
```
PASSED tests/unit/test_validator.py::test_manifold_check
PASSED tests/unit/test_executor.py::test_sandbox_timeout
PASSED tests/unit/test_executor.py::test_sandbox_no_network
PASSED tests/unit/test_dimension_parser.py::test_parse_mm_value
...
```

---

## 3. Production Deployment

### 3.1 Additional Prerequisites

```bash
sudo apt-get install -y docker.io docker-compose-plugin postgresql-15
```

### 3.2 Docker Compose Stack

```yaml
# docker-compose.yml (production)
version: "3.9"
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://mech:${DB_PASSWORD}@db:5432/mech_cad
      - REDIS_URL=redis://redis:6379/0
      - ARTIFACT_STORE_BACKEND=local
      - ARTIFACT_STORE_PATH=/data/artifacts
      - AUTH_DISABLED=false
    volumes:
      - artifact_data:/data/artifacts
    depends_on: [db, redis]

  worker:
    build: .
    command: rq worker mech-cad-jobs --url redis://redis:6379/0
    environment:
      - DATABASE_URL=postgresql://mech:${DB_PASSWORD}@db:5432/mech_cad
      - REDIS_URL=redis://redis:6379/0
      - ARTIFACT_STORE_PATH=/data/artifacts
    volumes:
      - artifact_data:/data/artifacts
    depends_on: [db, redis]
    deploy:
      replicas: 4   # Adjust to CPU count

  executor:
    # Isolated container for CAD code execution — no secrets, no DB access
    build:
      context: .
      dockerfile: Dockerfile.executor
    network_mode: none   # NO network access
    read_only: true
    tmpfs: ["/workspace:size=512m", "/tmp:size=128m"]
    security_opt: ["no-new-privileges:true"]
    cap_drop: ["ALL"]

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: mech_cad
      POSTGRES_USER: mech
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes: [pg_data:/var/lib/postgresql/data]

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes: [redis_data:/data]

volumes:
  artifact_data:
  pg_data:
  redis_data:
```

### 3.3 PostgreSQL Migration

```bash
# Switch DATABASE_URL to PostgreSQL
export DATABASE_URL=postgresql://mech:password@localhost:5432/mech_cad

# Run migrations
python -m mech_cad db upgrade

# Verify connection
python -m mech_cad db status
```

### 3.4 HTTPS / Reverse Proxy

Put Nginx or Caddy in front of the API service. Example Caddy config:

```caddyfile
mech-cad.yourdomain.com {
    reverse_proxy localhost:8000
    encode gzip
}
```

---

## 4. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `sqlite:///./data/mech_cad.db` | SQLAlchemy database URL |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection URL |
| `ARTIFACT_STORE_PATH` | Yes | `./data/artifacts` | Base path for artifact storage |
| `ARTIFACT_STORE_BACKEND` | No | `local` | `local` or `s3` |
| `OPENAI_API_KEY` | No | — | OpenAI GPT API key |
| `GOOGLE_API_KEY` | No | — | Google Gemini API key |
| `ANTHROPIC_API_KEY` | No | — | Anthropic Claude API key |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `DEFAULT_VISION_PROVIDER` | No | `ollama` | Default VLM provider |
| `DEFAULT_VISION_MODEL` | No | `llama3.2-vision:11b` | Default VLM model |
| `AUTH_DISABLED` | No | `false` | Disable auth for dev |
| `API_SECRET_KEY` | No | random | JWT signing key |
| `LOG_LEVEL` | No | `INFO` | DEBUG/INFO/WARNING/ERROR |
| `JOB_TIMEOUT_SECONDS` | No | `600` | Max wall time per job |
| `CAD_EXEC_TIMEOUT_SECONDS` | No | `60` | Max CAD code execution |
| `MAX_UPLOAD_BYTES` | No | `52428800` | Max file upload (50 MB) |
| `MAX_CONCURRENT_JOBS` | No | `4` | RQ worker concurrency |

---

## 5. Backup and Recovery

### 5.1 Database Backup

```bash
# SQLite
cp data/mech_cad.db data/mech_cad.db.$(date +%Y%m%d)

# PostgreSQL
pg_dump -U mech mech_cad | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 5.2 Artifact Store Backup

```bash
# Rsync artifacts to backup location
rsync -av data/artifacts/ /backup/mech_cad_artifacts/
```

### 5.3 Recovery

1. Stop all workers: `rq info --url redis://localhost:6379/0` → drain queues
2. Stop API server
3. Restore database from backup
4. Restore artifact store
5. Restart services
6. Re-queue any jobs that were `running` at crash time (they will retry)

---

## 6. Health Checks

```bash
# API health
curl http://localhost:8000/health
# → {"status": "ok", "db": "connected", "redis": "connected", "workers": 2}

# Worker status
rq info --url redis://localhost:6379/0

# Benchmark smoke test
python -m mech_cad benchmark run --case A001 --quick
```

---

## 7. Upgrading

```bash
# Pull latest code
git pull origin main

# Install new dependencies
uv pip install -e ".[dev]"

# Run database migrations (always before restarting services)
python -m mech_cad db upgrade

# Restart services
# (Docker Compose)
docker compose up -d --build
```

> [!WARNING]
> Never skip `db upgrade` after pulling new code. Database schema changes are not backward compatible. Running old code against a new schema will cause data corruption.

---

## 8. Known Setup Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `libGL.so.1: cannot open shared object` | Missing GL library for PaddleOCR | `sudo apt-get install libgl1` |
| `cadquery` fails to import on arm64 | CadQuery wheels not available for all ARM targets | Use x86_64 or build from source |
| Ollama model download fails | Insufficient disk space | Ensure ≥10 GB free for 11B model |
| `rq worker` exits immediately | Redis not running | Start Redis first |
| SQLite `database is locked` | Multiple writers | Switch to PostgreSQL for multi-worker |
