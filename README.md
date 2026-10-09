# MECH AI ADDON — 2D Engineering Drawing to 3D CAD Platform

> **Version:** 0.1.0 (Milestone 1)  
> **Status:** Active development — not production-ready

## What This Is

An enterprise-grade platform that converts 2D engineering drawings into geometrically validated 3D CAD models (STEP format), with independent validation, learning from failures, and a full web interface for review and correction.

**This is an engineering system, not a demo.** Success is measured by geometric accuracy on unfamiliar drawings, not by how impressive the UI looks.

## Quick Start

### Prerequisites

- Linux (Ubuntu 22.04+ or Debian 12+)
- Python 3.11+
- Redis
- (Optional) Ollama for local AI inference
- (Optional) Cloud API key for higher-quality results

### Installation

```bash
# Install system dependencies
sudo apt-get update && sudo apt-get install -y \
    python3.11 python3.11-venv redis-server \
    libgomp1 libgl1 libglib2.0-0 libmagic1

# Install uv package manager
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env

# Install project
cd "MECH AI ADDON"
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env — at minimum set DATABASE_URL and ARTIFACT_STORE_PATH

# Initialize database
python -m mech_cad db upgrade

# (Optional) Install Ollama and pull a model for local inference
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.2-vision:11b
```

### Run

```bash
# Terminal 1 — API server
uvicorn mech_cad.api.main:app --reload --port 8000

# Terminal 2 — Job worker
rq worker mech-cad-jobs --url redis://localhost:6379/0

# Terminal 3 — Redis (if not running as service)
redis-server
```

Open `http://localhost:8000` for the web UI.

### Verify

```bash
python -m pytest tests/unit/ -v
```

## Architecture

See [`docs/target_architecture.md`](docs/target_architecture.md) for full system design.

```
Upload Drawing → Quality Assessment → View Detection → Dimension Extraction
    → Constraint Reconstruction → Feature Plan → CAD Construction (sandboxed)
    → Kernel Validation → Projection Comparison → Acceptance Policy
    → Export (STEP + STL + GLB) → Job Record + Learning
```

## Documentation

| Document | Description |
|----------|-------------|
| [`docs/architecture_audit.md`](docs/architecture_audit.md) | Audit of CAD3Dify and Agent3Dify reference repos |
| [`docs/reference_repository_comparison.md`](docs/reference_repository_comparison.md) | Side-by-side comparison and reuse decisions |
| [`docs/target_architecture.md`](docs/target_architecture.md) | Full system design |
| [`docs/implementation_roadmap.md`](docs/implementation_roadmap.md) | Milestone plan |
| [`docs/geometry_validation.md`](docs/geometry_validation.md) | Validation subsystem |
| [`docs/failure_learning_system.md`](docs/failure_learning_system.md) | Failure recording and retrieval |
| [`docs/security_model.md`](docs/security_model.md) | Threat model and sandbox design |
| [`docs/benchmarking.md`](docs/benchmarking.md) | Metrics and benchmark methodology |
| [`docs/deployment.md`](docs/deployment.md) | Setup and deployment guide |
| [`docs/known_limitations.md`](docs/known_limitations.md) | Current limitations |

## Supported Drawing Types

- JPEG, PNG, TIFF, BMP raster images
- PDF (first page, raster extraction)
- Single-part mechanical drawings with orthographic projection

## Not Supported (v0.1)

- Assembly drawings
- DXF / DWG vector formats
- GD&T tolerance modeling
- Free-form NURBS surfaces
- Multi-page drawings

## License

MIT

## Acknowledgments

Architecture informed by (but not copied from):
- [CAD3Dify](https://github.com/neka-nat/cad3dify) by neka-nat (MIT)
- [Agent3Dify](https://github.com/neka-nat/agent3dify) by neka-nat (MIT)

See [`docs/reference_repository_comparison.md`](docs/reference_repository_comparison.md) for what was reused, what was rewritten, and why.
