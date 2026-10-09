# Risks and Trade-offs

> **Date:** 2026-10-10

---

## 1. Fundamental Risks

### R1 — LLM Dimensional Hallucination (CRITICAL)
**Risk:** The VLM estimates feature dimensions from pixel positions rather than reading explicit annotations.  
**Impact:** Generated STEP dimensions may be 10–1000× off from actual drawing.  
**Mitigation:** OCR-based dimension extraction; kernel bounding-box check against extracted dims; explicit "unknown dimension" tagging when OCR confidence is low.  
**Residual Risk:** OCR may also fail on complex drawings; residual error reported as "uncalibrated estimate."

### R2 — Invalid B-rep Geometry (HIGH)
**Risk:** CadQuery Boolean operations can produce non-manifold or open geometry that exports as STEP but cannot be machined or imported into downstream CAD tools.  
**Impact:** Customer receives a geometrically invalid file with no warning.  
**Mitigation:** BRepCheck_Analyzer after every construction; STEP re-import verification; explicit rejection of invalid B-rep.

### R3 — Sandbox Escape (HIGH, LOW probability)
**Risk:** LLM-generated code exploits a sandbox misconfiguration to access the host filesystem, read API keys, or exfiltrate drawings.  
**Impact:** Data breach or credential compromise.  
**Mitigation:** Defense-in-depth: `resource` limits + restricted env vars + no network in subprocess + Docker container in production + no application module paths in PYTHONPATH.  
**Known residual:** Subprocess-only isolation is weaker than container. Document this clearly; require Docker in production.

### R4 — Incorrect 3D Reconstruction from 2D (HIGH)
**Risk:** A single 2D view (or even three 2D views) rarely uniquely determines the 3D shape, especially for hidden features, internal geometry, or ambiguous depth.  
**Impact:** Generated model may be plausible but geometrically incorrect.  
**Mitigation:** Multi-view correspondence checking; explicit DOF tracking; ambiguity reporting to user; human review workflow.

---

## 2. Trade-off Decisions

### T1 — Structured Feature Plan vs. Raw Code Generation
**Decision:** Use structured JSON FeaturePlan (validated schema) instead of raw code generation.  
**Trade-off:** More rigid (harder for LLM to express unusual shapes) but more traceable and correctable.  
**Rationale:** Correctness requires traceability. Raw code generation makes it impossible to diagnose which feature produced an incorrect dimension.

### T2 — CadQuery vs. Build123d
**Decision:** Use CadQuery as primary kernel; design code so Build123d can substitute.  
**Trade-off:** CadQuery has more training signal for LLMs (more GitHub examples); Build123d has a more modern API.  
**Rationale:** LLM code generation quality is directly related to training data volume. CadQuery wins on that metric today.

### T3 — SQLite vs. PostgreSQL
**Decision:** SQLite for development; PostgreSQL target for multi-user production.  
**Trade-off:** SQLite is simpler but has write-contention limits under concurrent workers.  
**Rationale:** Minimize setup friction for contributors; preserve clear migration path.

### T4 — RQ vs. Celery vs. In-Process Threading
**Decision:** Redis + RQ for task queue.  
**Trade-off:** Requires Redis; Celery is more feature-rich but significantly more complex.  
**Rationale:** RQ is simpler, well-documented, sufficient for initial throughput targets. Redis also serves as cache.

### T5 — Acceptance Policy (Deterministic) vs. LLM Judgment
**Decision:** Acceptance is fully deterministic (metric thresholds, configurable).  
**Trade-off:** Cannot capture nuanced geometric correctness that metrics miss.  
**Rationale:** The system must not lie to users. If metrics cannot determine correctness, the result is `needs_review`, not `accepted`. An LLM can claim anything is correct; metrics are falsifiable.

### T6 — Local OCR (PaddleOCR) vs. Cloud OCR (Google Vision)
**Decision:** PaddleOCR as default; Google Cloud Vision as optional enhancement.  
**Trade-off:** PaddleOCR is slower and less accurate on complex engineering drawings than Google Vision.  
**Rationale:** The system must work offline. Cloud OCR is an enhancement, not a requirement.

---

## 3. Known Limitations at Launch

1. **Assembly drawings**: Not supported. Only single-part drawings.
2. **DXF vector input**: Not supported in Milestone 1.
3. **GD&T tolerances**: Detected but not modeled (noted in validation report).
4. **Threads and surface finish**: Simplified or omitted.
5. **Dimensional accuracy on complex parts**: Insufficient for precision machining without human verification.
6. **Free-form surfaces**: Not supported (no NURBS construction in CadQuery script).
7. **OCR on handwritten annotations**: Unreliable; flagged as low confidence.
8. **Drawing quality below threshold**: Processing stops with explicit rejection reason.
9. **Local 11B models**: Significantly lower quality than GPT-4o/Gemini Pro. Results classified as `needs_review` at higher rate.
10. **Offline mode**: Works with Ollama; quality trade-off is significant and documented.
