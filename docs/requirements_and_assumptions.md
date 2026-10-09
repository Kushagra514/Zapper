# Requirements and Assumptions

> **Date:** 2026-10-10  
> **Status:** Initial version — gaps noted where requirements are underdetermined

---

## 1. Input Requirements

### 1.1 Supported Input Formats (Initial Scope)
- **Raster images**: JPEG, PNG, TIFF, BMP (primary)
- **PDF** (planned): raster extraction per page via `pypdf` or `pdf2image`
- **DXF** (future): vector CAD drawing format — out of scope for Milestone 1

### 1.2 Drawing Types Supported
- Single-part mechanical drawings with orthographic projection (front/top/right/left/bottom/isometric)
- Drawings with explicit dimension annotations
- Drawings with visible edges, hidden lines (dashed), centerlines
- Scanned drawings (grayscale or color, moderate noise acceptable)

### 1.3 Drawing Types Explicitly Out of Scope (Initial)
- Assembly drawings with multiple parts and part callouts
- Sheet metal unfold/bend drawings
- Exploded-view drawings
- GD&T tolerance callouts (noted but not parsed in Milestone 1)
- Thread forms, surface finish symbols (noted, not modeled)
- Weld symbols

---

## 2. Output Requirements

### 2.1 Primary Deliverable
- **STEP (ISO 10303-21)** — parametric B-rep solid, re-importable into MCAD tools
- Must export without kernel errors
- Must re-import cleanly (validated in pipeline)

### 2.2 Secondary Deliverables
- **STL** — triangulated mesh for 3D printing inspection
- **GLB/GLTF** — browser-viewable 3D for inline UI preview

### 2.3 Reporting Outputs
- Validation report (JSON + human-readable summary)
- Extracted drawing evidence (dimensions, views, features)
- CAD feature plan (structured JSON)
- Construction history and parameter values
- Acceptance status: `accepted | accepted_with_warnings | needs_review | rejected | failed`

---

## 3. Geometric Scope

### 3.1 Feature Types Supported (Milestone 2+)
- Prismatic extrusions (box, prism with complex cross-section)
- Cylindrical features (round stock, bosses, shafts)
- Through-holes, counterbores, countersinks
- Slots, pockets, steps
- Fillets and chamfers on edges
- Linear and circular patterns of features
- Symmetric and mirrored features

### 3.2 Feature Types Out of Scope (Milestone 1)
- Free-form NURBS surfaces
- Complex lofts and sweeps
- Multi-body parts
- Springs, threads (modeled as simplified cylinders)

---

## 4. AI Model Requirements

### 4.1 Must Work With
- **Free/open-weight**: Ollama-served models (LLaMA 3.2 Vision, Qwen2-VL, LLaVA)
- **Hosted free-tier**: Google Gemini Flash free tier (subject to rate limits)
- **Optional paid**: OpenAI GPT-4o, Google Gemini Pro, Anthropic Claude

### 4.2 Assumptions
- **[ASSUMPTION A1]** The host machine may not have a GPU. We must support CPU-only inference with reduced quality.
- **[ASSUMPTION A2]** Free hosted APIs (Gemini Flash free tier) are rate-limited. We must implement retry-with-backoff and cost tracking.
- **[ASSUMPTION A3]** OCR (for dimension extraction) can use local Tesseract or hosted Google Vision — both must be supported.

---

## 5. Performance and Scalability

### 5.1 Initial Targets (Milestone 5)
- **Concurrent jobs**: ≥4 parallel conversions with 4 CPU cores
- **Latency**: < 3 minutes median for a simple part with paid cloud model
- **Latency (local model)**: < 10 minutes median for a simple part
- **Valid STEP rate**: target ≥ 70% on simple prismatic parts

### 5.2 Assumptions
- **[ASSUMPTION A4]** Initial deployment is single-server (Linux, 16 GB RAM, no GPU required).
- **[ASSUMPTION A5]** Object storage (for large artifacts) can be a local directory in development; S3-compatible in production.
- **[ASSUMPTION A6]** Database is SQLite for development, PostgreSQL for multi-user production.

---

## 6. Security Requirements

### 6.1 Non-Negotiable
- Generated CAD code must NOT execute with host process privileges
- Generated code must run in a subprocess with: non-root UID, no network, restricted filesystem, CPU+memory limits, wall-clock timeout
- API keys must not appear in logs, UI, or API responses
- User-uploaded files must be validated (MIME type, size limit) before processing

### 6.2 Assumptions
- **[ASSUMPTION A7]** Full container sandboxing (Docker) is the target for production. Development may use restrictive subprocess + `resource` module limits.
- **[ASSUMPTION A8]** No multi-tenant user authentication is required for Milestone 1 (single-user local deployment).

---

## 7. Data Sensitivity

- **[ASSUMPTION A9]** Engineering drawings may be proprietary. The system must not send drawings to external APIs unless the user has explicitly configured external model providers.
- When using local Ollama models, drawings stay on-premise.
- External API calls are logged with a flag indicating data was transmitted externally.

---

## 8. Validation Requirements

### 8.1 Kernel-Level (Required for Acceptance)
- STEP export succeeds
- STEP re-import succeeds
- Solid is manifold (no open shells)
- Bounding box dimensions within ±10% of extracted drawing dimensions (where available)

### 8.2 Projection-Level (Required for `accepted` Status)
- IoU silhouette overlap ≥ 0.75 for each available orthographic view
- Edge-mask similarity ≥ 0.65

### 8.3 Dimensional (Required for `accepted` with dimensional evidence)
- Extracted dimension values exist and have been checked against STEP bounding box
- Discrepancy < configured tolerance (default: 5%)

---

## 9. Feedback and Learning Requirements

### 9.1 Required
- Every conversion attempt is persisted (job record + attempt record)
- Failed attempts retain: input file, extracted evidence, error category, CAD logs
- Human reviewer can approve/reject/correct a result
- Corrections are stored with provenance (original attempt + correction)

### 9.2 Not Required (Milestone 1-4)
- Automatic fine-tuning on collected data
- RAG retrieval from case library (planned Milestone 4)

---

## 10. UI Requirements

### 10.1 Functional Requirements
- Upload drawing (drag-and-drop or file picker)
- View upload preview and quality assessment
- Confirm units and key assumptions before starting
- Track conversion progress by stage
- View 3D model in browser (GLB preview)
- Download STEP, STL, GLB
- View validation report and warnings
- Submit corrections or feedback
- View job history

### 10.2 Non-Functional
- Responsive layout (desktop primary, mobile secondary)
- Clear empty/loading/warning/success/failure states
- No internal agent terminology exposed to users

---

## 11. Gap Register

| Gap ID | Description | Impact | Resolution |
|--------|-------------|--------|-----------|
| G1 | No benchmark drawings available in workspace | Cannot establish baseline metrics | Milestone 1: collect sample drawings |
| G2 | No reference STEP models available | Cannot compute 3D geometric accuracy | Milestone 2: source or generate reference models |
| G3 | GD&T parsing scope undefined | May need to note tolerances in report | Out of scope Milestone 1, noted in output |
| G4 | Throughput target not validated | 3-minute target is estimated | Baseline measurement in Milestone 2 |
| G5 | Open-weight model quality unknown | May need paid model for acceptable quality | Experiment in Milestone 1 |
