# Known Limitations

> **Date:** 2026-10-10  
> **Version:** 0.1.0 (Initial)  
> **Update policy:** This document is updated whenever a new limitation is confirmed or a listed limitation is resolved.

---

## 1. Drawing Input Limitations

### L1 — Assembly Drawings Not Supported
**Status:** Out of scope (Milestone 1–6)  
**Impact:** Assembly drawings with multiple parts, part callouts, bills of materials, or part numbers will be rejected with `INVALID_INPUT` or produce incorrect single-part geometry.  
**Workaround:** Extract individual part drawings and process each separately.

### L2 — DXF / CAD Vector Formats Not Supported
**Status:** Planned (post-Milestone 6)  
**Impact:** DXF, DWG, IGES, and other vector CAD formats are not accepted. Only raster images (JPEG, PNG, TIFF, BMP) and PDF (raster extraction only) are supported.  
**Workaround:** Export drawing as high-resolution JPEG or PNG from your CAD tool.

### L3 — Multi-Page Drawings: First Page Only
**Status:** Milestone 1 limitation  
**Impact:** PDF files with multiple sheets will have only the first page processed.  
**Workaround:** Export individual drawing sheets as separate PDFs or images.

### L4 — Handwritten Dimension Annotations
**Status:** Known limitation  
**Impact:** Handwritten or script-font dimension values are unreliably extracted by PaddleOCR. They will be flagged as low-confidence and the model classified as `needs_review`.

### L5 — Very Low Resolution Images
**Status:** Known limitation  
**Impact:** Images below approximately 300 DPI equivalent (where dimension text is < 8px tall) produce unreliable OCR. Drawing quality assessment will warn, but processing continues.  
**Threshold:** Blur score below configurable threshold triggers `LOW_DRAWING_QUALITY` warning.

### L6 — Non-Standard Drawing Layouts
**Status:** Known limitation  
**Impact:** Drawings that do not follow standard orthographic projection layouts (e.g., third-angle or first-angle projection in standard positions) may have views misidentified or associated incorrectly.

---

## 2. Geometry Limitations

### L7 — Free-Form NURBS Surfaces Not Supported
**Status:** Out of scope (fundamental limitation of CadQuery parametric approach)  
**Impact:** Parts with sculptural, organic, or aerodynamic surfaces cannot be reconstructed from standard engineering drawings. The system can approximate with prismatic/cylindrical features but results will be incorrect.

### L8 — Single Part Only (No Assemblies)
**Status:** Out of scope  
**Impact:** Multi-body configurations where separate solid parts must remain disconnected are not supported. CadQuery boolean operations merge touching solids.

### L9 — Threads Not Modeled Accurately
**Status:** Known limitation  
**Impact:** Thread forms (metric, UNC, etc.) are represented as smooth cylinders or simple circular features. Thread callouts (e.g., M10×1.5) are noted in the validation report but not geometrically modeled.

### L10 — Weld Symbols Ignored
**Status:** Out of scope  
**Impact:** Weld joint geometry, weld beads, and weld preparation forms are not modeled. Weld symbols are not interpreted.

### L11 — GD&T Tolerances Noted but Not Modeled
**Status:** Partial support (Milestone 4+)  
**Impact:** GD&T callouts (flatness, perpendicularity, true position, etc.) are detected and noted in the evidence report but do not affect the generated geometry. Nominal geometry is generated; tolerance zones are not represented.

### L12 — Complex Fillets and Chamfers May Fail
**Status:** Known failure mode  
**Impact:** CadQuery fillet operations on non-manifold or complex topology can raise exceptions. The pipeline catches these and falls back to generating the model without the fillet, recording the failure.

---

## 3. AI and Inference Limitations

### L13 — Local 11B Models Significantly Less Accurate Than Cloud Models
**Status:** Confirmed limitation  
**Impact:** With Ollama-served LLaMA 3.2 Vision 11B, feature plan quality is substantially lower than with GPT-4o or Gemini 1.5 Pro. Expect higher `needs_review` rate, lower IoU scores, and more dimensional errors.  
**Measurement:** Not yet benchmarked with reference STEP models. This is an engineering expectation, not a measured quantity.  
**Workaround:** Configure a cloud model provider if quality is insufficient.

### L14 — Dimensional Accuracy on Complex Parts Is Insufficient for Precision Machining
**Status:** Fundamental limitation until calibrated with reference measurements  
**Impact:** Extracted dimensions may have errors up to ±10-20% even with OCR extraction. Parts intended for precision machining must have all dimensions verified by a domain expert before use.  
**Required action:** Human review for any part where dimensional accuracy is critical.

### L15 — Depth Dimension Often Unreliable
**Status:** Fundamental limitation of 2D-to-3D inference  
**Impact:** When no depth dimension is explicitly annotated (e.g., on the side view), depth is estimated by the VLM from the drawing's visual proportions. This estimate may be significantly incorrect.  
**Explicit reporting:** Every validation report notes which dimensions were extracted vs. estimated.

### L16 — Single-View Drawings Have Unresolvable Ambiguity
**Status:** Fundamental limitation  
**Impact:** A single orthographic view cannot uniquely determine depth, hidden features, or internal geometry. The system generates the most likely interpretation and flags the ambiguity explicitly. Multiple interpretations are not generated automatically.

### L17 — Gemini Free-Tier Rate Limits
**Status:** Operational limitation  
**Impact:** Google Gemini free tier is limited to 15 requests per minute (as of 2026-10). High job throughput will hit this limit and trigger retry-with-backoff delays.  
**Mitigation:** Exponential backoff (already implemented). For higher throughput, use a paid API key or local Ollama.

---

## 4. Validation Limitations

### L18 — No 3D Geometric Accuracy Without Reference STEP
**Status:** Fundamental limitation  
**Impact:** Without a reference STEP file from a trusted source, 3D geometric metrics (volume error, surface distance) cannot be computed. The system can only measure: valid B-rep topology, bounding box dimensions, and 2D projection similarity.  
**Required for full validation:** Reference STEP models from human expert or physical measurement.

### L19 — Projection Comparison Cannot Detect Depth Errors
**Status:** Fundamental limitation (documented in every validation report)  
**Impact:** A model can pass all 2D projection similarity checks while having an incorrect depth dimension. The validation report explicitly states this limitation.

### L20 — Acceptance Thresholds Are Uncalibrated
**Status:** Known limitation (Milestone 1)  
**Impact:** The default IoU ≥ 0.75 and dimensional error ≤ 5% thresholds are engineering estimates without statistical backing. Actual false-positive and false-negative rates are unknown.  
**Resolution path:** Calibrate thresholds against a benchmark set with verified reference models (Milestone 2+).

---

## 5. System Limitations

### L21 — Subprocess Sandbox Not Equivalent to Container Isolation
**Status:** Development-mode limitation  
**Impact:** The `resource`-module sandbox reduces blast radius but does not prevent all escape vectors (network access, host filesystem reads via absolute paths, same-user process inspection).  
**Required for production:** Docker container per job with `--network none --cap-drop ALL`.

### L22 — SQLite Write Contention Under Load
**Status:** Known limitation for concurrent workers  
**Impact:** SQLite has write serialization that limits throughput under 4+ concurrent job workers.  
**Resolution:** Switch `DATABASE_URL` to PostgreSQL for multi-worker deployments.

### L23 — No Fine-Tuning or Model Improvement Pipeline
**Status:** Deferred (post-Milestone 6)  
**Impact:** The system learns from failures only through retrieval of verified past cases. No mechanism exists to improve model weights from accumulated data.

### L24 — Windows Not Supported
**Status:** Known limitation  
**Impact:** The `resource` module for process limits is Linux/macOS only. The `preexec_fn` mechanism is Unix-only. Windows deployment requires Docker with Linux containers.

---

## 6. Limitation Resolution Roadmap

| Limitation | Target Milestone | Priority |
|------------|-----------------|---------|
| L20 (uncalibrated thresholds) | M2 | HIGH |
| L21 (sandbox hardening) | M4 | HIGH |
| L22 (SQLite contention) | M4 | MEDIUM |
| L13 (local model quality measured) | M1 | MEDIUM |
| L18 (reference STEP collection) | M2 | HIGH |
| L3 (multi-page PDF) | M3 | LOW |
| L7 (NURBS surfaces) | Post-M6 | LOW |
| L1 (assemblies) | Post-M6 | LOW |
| L2 (DXF input) | Post-M6 | LOW |
