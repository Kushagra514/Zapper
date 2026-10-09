# Implementation Roadmap

> **Date:** 2026-10-10  
> **Approach:** Incremental milestones, each delivering a testable vertical slice before expanding scope

---

## Milestone 1 — Understand, Baseline, and First Working Slice
**Target:** 2 weeks  
**Goal:** A working end-to-end conversion path from image to STEP, with explicit validation output

### Deliverables
- [ ] Project skeleton and dependency setup (`pyproject.toml`, `uv`, virtual env)
- [ ] Drawing ingestion module (`s01_ingest.py`): load JPEG/PNG, MIME check, size limit
- [ ] Quality assessment module (`s02_quality.py`): blur + skew detection
- [ ] CadQuery executor with subprocess sandbox (`cad/executor.py`)
- [ ] CadQuery kernel validator (`cad/validator.py`): STEP export/re-import, manifold check
- [ ] Basic VLM-to-CadQuery generation (FeaturePlan schema → code template → execute)
- [ ] Provider interface + Ollama provider + at least one cloud provider
- [ ] SQLite database with Job and Attempt records
- [ ] FastAPI: POST /jobs, GET /jobs/{id}, GET /jobs/{id}/artifacts/{name}
- [ ] Basic web UI: upload → progress (polling) → download
- [ ] Initial benchmark: 5 sample drawings, record baseline success rate and validation results

### Success Criteria
- A JPEG drawing can be uploaded and a STEP file downloaded
- The STEP re-imports without error in the pipeline
- Concurrent jobs do not overwrite each other's outputs
- No unhandled exceptions bubble to the API response

---

## Milestone 2 — Geometry Reasoning and Better Validation
**Target:** 3 weeks after M1  
**Goal:** Measurable improvement in dimensional accuracy through OCR + constraint extraction

### Deliverables
- [ ] OCR module (`drawing/ocr.py`): PaddleOCR integration, dimension value extraction
- [ ] View detector (`drawing/view_detector.py`): Hough + rectangle region detection
- [ ] DrawingEvidence schema with provenance tracking
- [ ] Constraint reconstruction (`s05_constraints.py`): 3D bounding dimensions from multi-view
- [ ] Dimensional validation (`validation/dimension_checks.py`): bounding box vs. extracted dims
- [ ] Projection comparison (`validation/projection_compare.py`): IoU + edge-mask + Hausdorff
- [ ] Acceptance policy (`validation/acceptance.py`): deterministic threshold evaluation
- [ ] Targeted refinement (`s11_refine.py`): per-feature correction based on validation failure
- [ ] Benchmark: same 5 drawings; compare M2 metrics against M1 baseline

### Success Criteria
- ≥1 dimension correctly extracted from ≥3/5 benchmark drawings
- Valid STEP rate ≥ 70% on simple prismatic benchmark cases
- Refinement reduces IoU failures (measured, not assumed)

---

## Milestone 3 — Persistence and Learning Infrastructure
**Target:** 2 weeks after M2  
**Goal:** Durable job history, failure recording, and basic case retrieval

### Deliverables
- [ ] Complete ORM schema with migrations (Alembic)
- [ ] DrawingEvidence, FeaturePlan, ValidationReport, HumanCorrection models in DB
- [ ] Artifact store abstraction (`persistence/artifact_store.py`): local FS
- [ ] Structured failure categories and recording
- [ ] Human review API: POST /jobs/{id}/review with correction payload
- [ ] Case library: retrieve similar verified cases by geometric metadata
- [ ] UI: job history page, review workflow, correction submission

### Success Criteria
- All jobs, attempts, and validation results persist across process restarts
- Human corrections are stored and linked to original attempts
- Retrieved similar cases are presented to the planner (measurable effect noted, not assumed)

---

## Milestone 4 — Safe Execution and Concurrency
**Target:** 2 weeks after M3  
**Goal:** Production-quality isolation, resource limits, and concurrent job handling

### Deliverables
- [ ] RQ worker setup with bounded concurrency
- [ ] Resource limits enforced in subprocess sandbox (CPU, memory, timeout, network=off)
- [ ] Per-job artifact namespacing (UUID-prefixed directories)
- [ ] Cancellation and timeout handling
- [ ] Worker crash recovery (re-queue interrupted jobs)
- [ ] Concurrency tests (≥4 parallel jobs without interference)
- [ ] Security audit: verify no API keys in logs, no path traversal, no code injection vector

### Success Criteria
- 4 concurrent jobs complete successfully without cross-contamination
- A job killed mid-execution leaves no corrupt artifacts
- Generated code cannot read application database credentials

---

## Milestone 5 — Enterprise UI and Observability
**Target:** 2 weeks after M4  
**Goal:** Polished web interface with real backend state, 3D viewer, and operational tooling

### Deliverables
- [ ] WebSocket or SSE for real-time stage progress
- [ ] three.js GLB viewer in UI
- [ ] Side-by-side drawing vs. render comparison view
- [ ] Validation report display (per-check pass/fail with explanations)
- [ ] Feature plan inspection panel
- [ ] Download buttons for STEP, STL, GLB
- [ ] Admin: job queue status, worker health
- [ ] Structured logging with trace IDs
- [ ] Deployment documentation

### Success Criteria
- All job states visible in real time
- 3D model viewable in browser without external tool
- Setup instructions work in a clean Linux environment

---

## Milestone 6 — Generalization and Optimization
**Target:** 3 weeks after M5  
**Goal:** Expand benchmark coverage, optimize model routing, reduce cost per accepted model

### Deliverables
- [ ] Benchmark expanded to ≥20 drawings covering multiple part families
- [ ] Performance by part category and drawing quality
- [ ] Model routing optimization: route simpler tasks to cheaper models (measured)
- [ ] Caching: cache VLM responses keyed to (input_hash, model, prompt_hash)
- [ ] Embedding-based retrieval evaluation: measure improvement from retrieved cases
- [ ] Cost tracking per job: provider calls, tokens, latency

### Success Criteria
- Benchmark results broken down by part family (no aggregate-only reporting)
- Cost per accepted model measurably reduced vs. Milestone 2 (with evidence)
- Retrieval benefit quantified on held-out cases

---

## Dependencies Between Milestones

```
M1 ──► M2 ──► M3
              │
              └──► M4 ──► M5 ──► M6
```

M4 is independent of M3 (can run in parallel with M3 if team capacity allows).

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| CadQuery fails on complex geometry | High | High | Add fallback strategies; record failure; human review |
| OCR fails on poor drawing quality | Medium | High | Fallback to VLM estimation; record as low-confidence |
| Open-weight models produce invalid CadQuery | High | Medium | Validate schema; retry; escalate to cloud model if configured |
| Gemini free tier rate limit hit | Medium | Medium | Backoff + model fallback; budget per job |
| Sandbox escape via generated code | Low | Critical | Defense-in-depth: resource limits + no network + container |
| LLM hallucinates dimensions | High | High | OCR provides ground truth; validation catches mismatches |

---

## Deferred Items (Post-M6)

- Fine-tuning on collected verified examples
- DXF vector input support
- Assembly drawing support
- GD&T tolerance parsing and modeling
- PDF vector extraction (beyond raster)
- Multi-page drawing support
- Automated regression suite with CI integration
