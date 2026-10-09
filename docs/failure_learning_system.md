# Failure Learning System

> **Date:** 2026-10-10  
> **Principle:** Failures are valuable data, but unverified failures must never become trusted training examples.

---

## 1. Purpose and Scope

The failure learning system exists to:

1. **Record** every conversion attempt with enough detail to diagnose why it failed
2. **Classify** failures into actionable categories (not just exception messages)
3. **Retrieve** relevant past cases to inform future conversion planning
4. **Protect** the knowledge base from contamination by unverified or incorrect models

It does **not**:
- Automatically fine-tune models on collected data
- Treat any failed or unverified attempt as a correct training target
- Claim retrieval improves results without measurement

---

## 2. What Is Recorded for Every Attempt

### 2.1 Mandatory Fields (All Attempts)

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | UUID | Parent job |
| `attempt_number` | int | 1-indexed within job |
| `started_at` / `completed_at` | datetime | Wall-clock timing |
| `stage_reached` | str | Last pipeline stage completed |
| `provider_model` | str | VLM used for this attempt |
| `acceptance_status` | enum | Final outcome |
| `failure_category` | enum | Structured failure type (see §3) |
| `failure_stage` | str | Stage where failure occurred |

### 2.2 Preserved Artifacts (All Attempts, Including Failed)

| Artifact | Condition |
|----------|-----------|
| Preprocessed drawing images | Always |
| OCR output JSON | When OCR ran |
| Detected view regions | When view detection ran |
| Extracted `DrawingEvidence` | When extraction ran |
| `FeaturePlan` JSON | When planner ran |
| Generated Python code | When code was generated |
| Execution stdout/stderr | When code ran |
| Generated STEP file | When construction produced any output |
| Rendered projection PNGs | When rendering ran |
| `KernelReport` JSON | When kernel checks ran |
| `ComparisonReport` JSON | When comparison ran |
| `ValidationReport` JSON | Always (may be partial) |

All artifacts stored in the artifact store with content-hash checksums. References stored in the database; binary files never in rows.

### 2.3 Sensitive Data Handling

- Provider API prompts are stored **hashed** (SHA-256 of prompt text) by default, not verbatim
- Verbatim prompt storage can be enabled by configuration for debugging
- Drawing content is never logged verbatim in structured log lines
- API keys are never stored anywhere

---

## 3. Failure Categories

Failures are classified into structured categories rather than raw exception text. This enables filtering, querying, and pattern recognition.

```python
class FailureCategory(str, Enum):
    # Input failures
    INVALID_INPUT = "invalid_input"           # Unsupported format, corrupt file
    LOW_DRAWING_QUALITY = "low_quality"       # Blur, skew, low contrast

    # Extraction failures
    OCR_FAILED = "ocr_failed"                 # PaddleOCR returned no text
    VIEW_DETECTION_FAILED = "view_detection_failed"
    DIMENSION_EXTRACTION_FAILED = "dim_extraction_failed"
    AMBIGUOUS_DRAWING = "ambiguous"           # Insufficient information for unique 3D shape

    # Planning failures
    FEATURE_PLAN_SCHEMA_INVALID = "plan_schema_invalid"
    FEATURE_PLAN_INCOMPLETE = "plan_incomplete"
    UNSUPPORTED_GEOMETRY = "unsupported_geometry"

    # Construction failures
    CADQUERY_SYNTAX_ERROR = "cq_syntax_error"
    CADQUERY_BOOLEAN_FAILURE = "cq_boolean_failure"
    CADQUERY_FILLET_FAILURE = "cq_fillet_failure"
    CADQUERY_EXPORT_FAILURE = "cq_export_failure"
    EXECUTION_TIMEOUT = "execution_timeout"
    EXECUTION_RESOURCE_LIMIT = "resource_limit"

    # Validation failures
    NON_MANIFOLD_GEOMETRY = "non_manifold"
    DIMENSIONAL_MISMATCH = "dimensional_mismatch"
    LOW_PROJECTION_SIMILARITY = "low_projection_iou"

    # Infrastructure failures
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_RATE_LIMIT = "rate_limit"
    PROVIDER_INVALID_RESPONSE = "invalid_provider_response"

    # Unknown
    UNKNOWN = "unknown"
```

### 3.1 Classification Logic

The pipeline classifier assigns a `FailureCategory` from the exception type, stage, and error message using a rule table. LLMs are not used for failure classification (too slow, non-deterministic).

---

## 4. Attempt State Machine

```
RAW_ATTEMPT
    │
    ├─► (pipeline runs) ─► COMPLETED
    │                           │
    │                     ┌─────┴──────┐
    │                     ▼            ▼
    │               ACCEPTED      FAILED/REJECTED
    │                                  │
    │                            FAILURE_DIAGNOSED
    │                                  │
    │                         (human reviews)
    │                                  │
    │                    ┌─────────────┴──────────────┐
    │                    ▼                             ▼
    │             HUMAN_REVIEWED_OK          HUMAN_REVIEWED_CORRECTED
    │                    │                             │
    │            GEOMETRY_VERIFIED               CORRECTION_STORED
    │                    │
    │          APPROVED_REUSABLE_CASE
    │
    └─► (manual exclusion) ─► EXCLUDED
```

Only `APPROVED_REUSABLE_CASE` status allows a record to be retrieved as a positive example.
`FAILED`, `REJECTED`, and `FAILURE_DIAGNOSED` records are retrievable as **negative examples** (warning cases).
No unverified attempt is ever presented as a trusted construction target.

---

## 5. Case Library and Retrieval

### 5.1 Purpose

When a new drawing arrives, the system retrieves similar past cases to:
- Provide the planner with successful construction strategies for similar geometry
- Warn about known failure modes for similar drawing types
- Suggest which features caused problems in past similar jobs

### 5.2 Retrieval Keys

Retrieval uses **structured metadata first**, embeddings second:

**Structured filters applied before similarity search:**
- `part_family` tag (if labeled): prismatic, cylindrical, sheet_metal, etc.
- Feature types present in drawing (holes, slots, fillets)
- Approximate bounding box aspect ratio (W:H:D)
- Number of orthographic views present
- Acceptance status (retrieve only `APPROVED_REUSABLE_CASE` for positive examples)

**Similarity search (secondary):**
- Embed the `DrawingEvidence` JSON as text → retrieve nearest neighbors via FAISS
- CLIP image embedding of the drawing → cosine similarity (supplementary only)

> [!WARNING]
> Image similarity alone is insufficient for retrieval. Two drawings that look similar may describe parts with different dimensions, topology, or manufacturing intent. Image embeddings are supplementary; structured metadata filters are primary.

### 5.3 What Retrieval Provides to the Planner

```json
{
  "retrieved_cases": [
    {
      "case_id": "...",
      "similarity_score": 0.87,
      "part_description": "Cylindrical boss with 3 through-holes on flange",
      "feature_plan_summary": "Base cylinder extrude → flange extrude → 3× hole pattern",
      "acceptance_status": "approved_reusable_case",
      "known_issues": [],
      "construction_notes": "Fillet radius must be applied after Boolean union"
    },
    {
      "case_id": "...",
      "similarity_score": 0.72,
      "part_description": "Similar flange drawing — FAILED",
      "feature_plan_summary": "N/A",
      "acceptance_status": "failure_diagnosed",
      "known_issues": ["Boolean union of boss and flange failed — ensure boss is fully contained in workplane"],
      "construction_notes": "N/A"
    }
  ]
}
```

### 5.4 Measuring Retrieval Benefit

Every job records whether retrieved cases were used and what the acceptance outcome was. The benefit of retrieval is measured by:

```
retrieval_benefit = acceptance_rate(jobs_with_retrieval) - acceptance_rate(jobs_without_retrieval)
```

This is computed on a held-out evaluation set, not the retrieval index itself. If retrieval shows no measurable benefit after 50+ evaluation cases, the retrieval strategy is revised.

---

## 6. Human Feedback Loop

### 6.1 Review Queue

Jobs with `needs_review` status appear in the reviewer queue. Reviewers see:
- Source drawing (original + preprocessed)
- Generated STEP (3D viewer)
- Validation report with specific failure reasons
- Diff images (drawing vs. rendered projection)
- Extracted dimensions (highlighting any mismatches)
- Feature plan tree

### 6.2 Reviewer Actions

| Action | System Effect |
|--------|--------------|
| **Approve** | Status → `geometry_verified`; eligible for retrieval if dimensions confirmed |
| **Reject** | Status → `human_reviewed_corrected` (negative case preserved) |
| **Correct dimensions** | New `HumanCorrection` record created; correction linked to attempt |
| **Upload reference STEP** | Reference stored as trusted artifact; 3D metrics computed |
| **Promote to case library** | Explicit promotion → `approved_reusable_case`; requires verify flag |

### 6.3 Correction Versioning

When a reviewer corrects a model:
- The original attempt and its artifacts are **never deleted**
- A `HumanCorrection` record links the corrected values to the original attempt
- Both versions are accessible from the UI
- The correction is tagged with reviewer ID and timestamp
- Provenance chain: `Attempt → HumanCorrection → Artifact`

---

## 7. What This System Does NOT Do

To prevent misunderstanding, the following are explicitly out of scope until justified by evidence:

1. **Automatic fine-tuning** on collected data — requires curated, deduplicated, licensed dataset
2. **Automatic promotion** of any result to training data — all promotion requires explicit human action
3. **Claiming retrieval "trains" the model** — retrieval provides context to the LLM; it does not update model weights
4. **Using failed attempts as positive training examples** — failed attempts are negative examples only
5. **Treating image similarity as a proxy for 3D geometric similarity** — explicitly noted as unreliable

---

## 8. Data Retention Policy

| Record Type | Retention |
|-------------|-----------|
| Accepted jobs (verified) | Indefinite |
| Failed jobs (diagnosed) | 90 days by default (configurable) |
| Infrastructure failures | 30 days |
| Raw input drawings | Per user data policy (default: job lifetime + 30 days) |
| Approved case library | Indefinite |
| Human corrections | Indefinite |
| Audit events | 1 year |

Retention is enforced by a scheduled cleanup task, not by cascade-delete rules. Artifact store files are cleaned separately from database records.
