# Target Architecture

> **Date:** 2026-10-10  
> **Version:** 1.0 (Initial design)

---

## 1. Design Principles

1. **Geometric correctness over visual resemblance** — every architectural decision is evaluated against this
2. **Deterministic where possible** — use OCR, OpenCV, and CAD-kernel checks before LLM judgment
3. **AI interprets, plans, and diagnoses** — AI does not execute unchecked code or judge its own output
4. **Independent validation** — the generator is never the sole judge of correctness
5. **Safe execution** — generated code runs in a sandboxed subprocess with resource limits
6. **Durable state** — every job, attempt, and validation result persists in a database
7. **Provider abstraction** — one interface supporting local Ollama, Gemini free tier, GPT-4o
8. **Measurable improvement** — no architectural claim without benchmark evidence

---

## 2. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web / API Layer                         │
│  FastAPI  ─────  Job API  ─────  WebSocket (progress)           │
│  Next.js / HTML UI   ─────  3D Viewer (three.js)               │
└───────────────────────────┬─────────────────────────────────────┘
                            │ (job submit / status poll)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Job Queue (RQ)                            │
│  Redis-backed ─── bounded workers ─── per-job isolation         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Conversion Pipeline                           │
│                                                                  │
│  Stage 1: Input Validation & Normalization                       │
│  Stage 2: Drawing Quality Assessment                             │
│  Stage 3: View & Annotation Detection                            │
│  Stage 4: Dimension & Feature Extraction (OCR + CV + VLM)       │
│  Stage 5: Constraint Reconstruction & 3D Hypothesis             │
│  Stage 6: Feature Plan Generation (structured JSON)             │
│  Stage 7: CAD Construction (CadQuery via sandboxed executor)    │
│  Stage 8: Kernel Validation (topology, manifold, dimensions)    │
│  Stage 9: Projection Rendering & Comparison                      │
│  Stage 10: Acceptance Policy Evaluation                         │
│  Stage 11: Targeted Refinement (if needed)                      │
│  Stage 12: Artifact Export (STEP, STL, GLB)                     │
│  Stage 13: Job Finalization & Learning Record                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                ┌───────────┴──────────┐
                ▼                      ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│   Model Providers    │  │           Persistent Store            │
│  - Ollama (local)    │  │  Database: SQLite → PostgreSQL        │
│  - Gemini (Google)   │  │  Artifacts: local FS → S3-compat.     │
│  - OpenAI (GPT)      │  │  Job records, attempts, validation    │
│  - Anthropic (Claude)│  │  Evidence, feature plans, feedback    │
│  Provider Interface  │  └──────────────────────────────────────┘
└──────────────────────┘
```

---

## 3. Module Structure

```
mech_cad/
├── api/
│   ├── main.py               # FastAPI application entry point
│   ├── routes/
│   │   ├── jobs.py           # POST /jobs, GET /jobs/{id}, DELETE /jobs/{id}
│   │   ├── artifacts.py      # GET /jobs/{id}/artifacts/{name}
│   │   ├── feedback.py       # POST /jobs/{id}/feedback
│   │   └── health.py         # GET /health
│   ├── models.py             # Pydantic request/response schemas
│   └── deps.py               # Shared dependencies (DB session, etc.)
│
├── pipeline/
│   ├── orchestrator.py       # Job runner: sequence stages, handle failures
│   ├── stages/
│   │   ├── s01_ingest.py     # Input validation, image loading, PDF extract
│   │   ├── s02_quality.py    # Blur, skew, contrast, completeness checks
│   │   ├── s03_detect_views.py   # Orthographic view detection + crop
│   │   ├── s04_extract_dims.py   # OCR + VLM dimension extraction
│   │   ├── s05_constraints.py    # 3D constraint reconstruction from views
│   │   ├── s06_feature_plan.py   # LLM → structured FeaturePlan JSON
│   │   ├── s07_cad_build.py      # FeaturePlan → CadQuery → sandboxed exec
│   │   ├── s08_validate.py       # Kernel checks, dimension verification
│   │   ├── s09_render_compare.py # Project STEP → views, compare to drawing
│   │   ├── s10_accept.py         # Acceptance policy evaluation
│   │   ├── s11_refine.py         # Targeted refinement on specific features
│   │   ├── s12_export.py         # STEP + STL + GLB artifact export
│   │   └── s13_finalize.py       # Record results, update job state
│   └── schemas.py            # StageInput/StageOutput base types
│
├── providers/
│   ├── base.py               # ModelProvider ABC
│   ├── ollama.py             # Ollama / OpenAI-compat local
│   ├── openai_provider.py    # OpenAI GPT
│   ├── google_provider.py    # Gemini
│   ├── anthropic_provider.py # Claude
│   ├── router.py             # Task → provider routing
│   └── registry.py           # Provider registry + capability checks
│
├── cad/
│   ├── executor.py           # Sandboxed subprocess runner
│   ├── validator.py          # CadQuery kernel checks
│   ├── renderer.py           # STEP → PNG projections
│   ├── feature_plan.py       # FeaturePlan Pydantic schema
│   └── templates/
│       └── base_template.py  # Python template for LLM code generation
│
├── drawing/
│   ├── ingestion.py          # File loading, MIME validation
│   ├── quality.py            # Quality assessment (blur, skew, contrast)
│   ├── view_detector.py      # Orthographic view detection
│   ├── ocr.py                # PaddleOCR + post-processing
│   ├── dimension_parser.py   # Dimension value extraction from OCR
│   └── evidence.py           # DrawingEvidence dataclass
│
├── validation/
│   ├── kernel_checks.py      # B-rep topology, manifold, solid count
│   ├── dimension_checks.py   # Bounding box vs. extracted dims
│   ├── projection_compare.py # IoU, edge-mask, Hausdorff distance
│   └── acceptance.py         # AcceptancePolicy evaluation
│
├── persistence/
│   ├── database.py           # SQLModel engine, session factory
│   ├── models.py             # ORM models (Job, Attempt, Evidence, etc.)
│   ├── migrations/           # Alembic migrations
│   └── artifact_store.py     # File store abstraction (local / S3)
│
├── worker/
│   ├── queue.py              # RQ queue setup
│   └── tasks.py              # RQ task: run pipeline for job
│
├── ui/
│   ├── index.html            # Single-page application
│   ├── app.js                # Main UI logic
│   ├── components/
│   │   ├── upload.js         # File upload with preview
│   │   ├── progress.js       # Stage-by-stage progress
│   │   ├── viewer3d.js       # three.js GLB viewer
│   │   ├── comparison.js     # Side-by-side drawing vs render
│   │   └── validation.js     # Validation report display
│   └── styles.css
│
├── config.py                 # Settings (env vars, Pydantic BaseSettings)
├── logging_config.py         # Structured loguru setup
└── tests/
    ├── unit/
    │   ├── test_ocr.py
    │   ├── test_dimension_parser.py
    │   ├── test_validator.py
    │   ├── test_executor.py
    │   └── test_feature_plan.py
    ├── integration/
    │   ├── test_pipeline_simple.py
    │   └── test_pipeline_concurrent.py
    └── benchmark/
        ├── cases/            # Sample drawings + expected properties
        └── run_benchmark.py
```

---

## 4. Conversion Pipeline — Stage-by-Stage Design

### Stage 1: Input Validation & Normalization
**Input:** Raw uploaded file bytes, metadata  
**Output:** NormalizedInput (image array, detected format, file checksum)  
**Validation:** MIME check, file size limit (configurable, default 50MB), non-zero dimensions  
**Error:** `InputRejected` with specific reason

### Stage 2: Drawing Quality Assessment
**Input:** NormalizedInput  
**Output:** QualityReport (blur score, skew angle, contrast range, DPI estimate, warnings)  
**Method:** OpenCV Laplacian variance (blur), Hough transform (skew), histogram (contrast)  
**Error:** Warning issued; processing continues unless quality is below hard threshold

### Stage 3: View Detection
**Input:** NormalizedInput + QualityReport  
**Output:** DetectedViews (list of (view_type, crop_box, confidence))  
**Method:** Classical: Hough lines + rectangular regions. VLM fallback for ambiguous layouts.  
**Failure mode:** Single-view or no-view-separation — continue with full image; record assumption

### Stage 4: Dimension & Feature Extraction
**Input:** NormalizedInput + DetectedViews  
**Output:** DrawingEvidence (list of ExtractedDimension, list of DetectedFeature)  
**Method:** PaddleOCR for text, heuristic for dimension arrows, VLM for complex annotations  
**Provenance:** Each extracted value tagged with: source view, image coordinates, method, confidence

### Stage 5: Constraint Reconstruction
**Input:** DrawingEvidence + DetectedViews  
**Output:** GeometricConstraints (width, height, depth, hole positions, symmetry axes, DOFs)  
**Method:** Geometric reasoning from cross-view correspondences, constraint solver  
**Ambiguity:** Unresolved DOFs recorded explicitly; not silently filled

### Stage 6: Feature Plan Generation
**Input:** GeometricConstraints + DrawingEvidence  
**Output:** FeaturePlan (JSON schema: ordered features with parameters, dependencies, expected dims)  
**Method:** VLM prompted to produce structured FeaturePlan JSON; validated against schema  
**Failure:** Schema validation fails → LLM retried with error message (max 3 attempts)

### Stage 7: CAD Construction
**Input:** FeaturePlan  
**Output:** CAD artifacts (model.step, model.stl) + build log  
**Method:** FeaturePlan → Python code generation → sandboxed subprocess execution  
**Sandbox:** Non-root, no network, read-only filesystem except designated output dir, 60s timeout, 2 GB memory

### Stage 8: Kernel Validation
**Input:** model.step  
**Output:** KernelReport (solid count, manifold status, bounding box, volume, issues list)  
**Method:** CadQuery re-import, OCC topology checker, BRepCheck_Analyzer  
**Failure:** Non-manifold or open shell → Rejected unless refinement resolves

### Stage 9: Projection Rendering & Comparison
**Input:** model.step + DetectedViews  
**Output:** ComparisonReport (per-view IoU, edge similarity, Hausdorff distance, diff images)  
**Method:** CadQuery render STEP → PNG at matched scale; OpenCV comparison  
**Limitation:** Records that 2D comparison cannot detect incorrect depth or hidden features

### Stage 10: Acceptance Policy
**Input:** KernelReport + ComparisonReport + DimensionalReport  
**Output:** AcceptanceResult (status: accepted | accepted_with_warnings | needs_review | rejected | failed)  
**Policy:** Configurable thresholds per check; part category can override defaults  
**No LLM**: Acceptance decision is deterministic based on metric thresholds

### Stage 11: Targeted Refinement
**Input:** AcceptanceResult + specific failure details  
**Output:** Updated FeaturePlan or corrected parameter values  
**Method:** Targeted prompt to VLM: "Feature X failed check Y with value Z. Suggest correction."  
**Limit:** Max 3 refinement iterations; each must make progress (validation scores must improve)

### Stage 12: Artifact Export
**Input:** Final model.step  
**Output:** Exported STEP (canonical), STL (mesh), GLB (browser), validation report PDF  
**Storage:** Artifact store (local FS or S3); references stored in database

### Stage 13: Finalization
**Input:** All stage outputs  
**Output:** Updated Job record, Attempt record, ValidationRecord  
**Learning:** Failure events written to failure log with structured category  
**State:** Job transitions to final state (completed/failed/needs_review)

---

## 5. Data Model (Database)

```
Job
  id: UUID
  status: enum (queued|running|completed|failed|needs_review|cancelled)
  created_at, started_at, completed_at
  input_artifact_id → Artifact
  config_snapshot: JSON

Attempt
  id: UUID
  job_id → Job
  attempt_number: int
  stage_reached: str
  started_at, completed_at
  result_artifact_id → Artifact (nullable)
  acceptance_status: enum
  failure_category: enum (nullable)

DrawingEvidence
  id: UUID
  job_id → Job
  view_type: str
  evidence_type: str (dimension|feature|annotation)
  value, unit, confidence: float
  source_coordinates: JSON
  extraction_method: str
  conflicting: bool

FeaturePlan
  id: UUID
  attempt_id → Attempt
  plan_json: JSON
  schema_version: str
  provider_model: str

ValidationReport
  id: UUID
  attempt_id → Attempt
  kernel_status: str
  is_manifold: bool
  bounding_box: JSON
  iou_scores: JSON
  edge_similarity_scores: JSON
  dimensional_errors: JSON
  acceptance_status: str
  human_reviewed: bool
  reviewer_id: str (nullable)
  reviewer_notes: str (nullable)

HumanCorrection
  id: UUID
  validation_report_id → ValidationReport
  corrected_dimensions: JSON
  corrected_features: JSON
  reference_artifact_id → Artifact (nullable)
  verified: bool
  eligible_for_retrieval: bool

Artifact
  id: UUID
  job_id → Job
  artifact_type: str (drawing|step|stl|glb|render|report)
  storage_path: str
  content_hash: str
  size_bytes: int
  created_at
```

---

## 6. Security Model

### 6.1 Sandboxed Code Execution

Generated Python code runs in a **subprocess** with:
```python
import subprocess, resource

def run_sandboxed(code: str, output_dir: Path, timeout: int = 60) -> dict:
    """Execute generated CadQuery code with resource limits."""
    script_path = output_dir / "generated_model.py"
    script_path.write_text(code)
    
    result = subprocess.run(
        ["python", str(script_path)],
        capture_output=True,
        timeout=timeout,
        cwd=str(output_dir),
        env={
            "PATH": "/usr/bin:/usr/local/bin",
            "HOME": str(output_dir),
            "PYTHONPATH": "",  # No access to application modules
        },
        # Resource limits via preexec_fn
        preexec_fn=_apply_resource_limits,
    )
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}

def _apply_resource_limits():
    # CPU time limit
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    # Memory limit (2 GB)
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    # File size limit (500 MB output)
    resource.setrlimit(resource.RLIMIT_FSIZE, (500 * 1024**2, 500 * 1024**2))
    # Process count
    resource.setrlimit(resource.RLIMIT_NPROC, (16, 16))
```

**Production target:** Docker container with `--network none --cap-drop ALL --read-only --tmpfs /tmp`.

### 6.2 Input Validation
- MIME type check + magic bytes check (PIL can verify image format)
- Maximum file size: 50 MB (configurable)
- Image dimensions: maximum 10,000×10,000 pixels
- PDF: maximum 50 pages; first page only in Milestone 1

### 6.3 API Security
- All API endpoints require authentication token (configurable; disabled in single-user dev mode)
- Artifact download URLs are time-limited (signed URLs or expiring tokens)
- API keys stored in environment variables, never in code or database
- Logs redact all API key prefixes with `****`

---

## 7. Provider Abstraction

```python
from abc import ABC, abstractmethod
from typing import Any

class ModelProvider(ABC):
    """Unified interface for all AI model providers."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def supports_vision(self) -> bool: ...

    @property
    @abstractmethod
    def supports_structured_output(self) -> bool: ...

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        response_format: type | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.1,
    ) -> str | dict: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

Concrete implementations: `OllamaProvider`, `OpenAIProvider`, `GoogleProvider`, `AnthropicProvider`.

**Router** selects provider per task based on:
1. Configuration preference
2. Provider availability check (ping)
3. Task capability requirements (vision, structured output)
4. Budget remaining for this job

---

## 8. Acceptance Decision Logic

```python
def evaluate_acceptance(
    kernel: KernelReport,
    comparison: ComparisonReport,
    dimensional: DimensionalReport,
    policy: AcceptancePolicy,
) -> AcceptanceResult:
    issues = []
    
    # Hard failures → Rejected
    if not kernel.export_succeeded:
        return AcceptanceResult(status="rejected", reason="STEP export failed")
    if not kernel.is_manifold:
        issues.append(Issue(code="NON_MANIFOLD", severity="error"))
    
    # Threshold checks → Accepted or Needs Review
    for view_id, iou in comparison.iou_scores.items():
        if iou < policy.min_iou:
            issues.append(Issue(code="LOW_IOU", view=view_id, value=iou, severity="warning"))
    
    if dimensional.has_extracted_dims:
        for dim_id, err in dimensional.relative_errors.items():
            if err > policy.max_dim_error:
                issues.append(Issue(code="DIM_ERROR", dim=dim_id, value=err, severity="error"))
    
    # Determine status
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]
    
    if errors:
        return AcceptanceResult(status="needs_review", issues=issues)
    elif warnings:
        return AcceptanceResult(status="accepted_with_warnings", issues=issues)
    else:
        return AcceptanceResult(status="accepted", issues=[])
```

**No LLM is invoked in acceptance evaluation.** The decision is fully deterministic.

---

## 9. Key Architectural Differences from Reference Repos

| Aspect | CAD3Dify | Agent3Dify | This System |
|--------|----------|------------|-------------|
| Execution safety | ❌ Unrestricted | ❌ Unrestricted | ✅ Sandboxed subprocess |
| Dimension extraction | ❌ Visual estimate | ❌ Visual estimate | ✅ OCR + CV + VLM |
| Validation | ❌ None | Partial (IoU only) | ✅ Kernel + projection + dimensional |
| Persistence | ❌ None | ❌ None | ✅ Database-backed |
| Learning | ❌ None | ❌ None | ✅ Failure recording + retrieval |
| Acceptance policy | ❌ Implicit pass | ❌ Implicit pass | ✅ Explicit deterministic policy |
| Feature plan | ❌ Raw code | ❌ Template only | ✅ Validated JSON schema |
| Open-weight models | Partial | ❌ None | ✅ Ollama + LangChain router |
| Multi-user | ❌ None | ❌ None | ✅ Job queue + isolated workspaces |
| UI | Basic Streamlit | CLI only | ✅ FastAPI + SPA with job history |
