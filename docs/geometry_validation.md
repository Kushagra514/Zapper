# Geometry Validation

> **Date:** 2026-10-10  
> **Principle:** The model generator must never be the sole judge of its own output.

---

## 1. Why Independent Validation Is Non-Negotiable

Both reference repositories (CAD3Dify, Agent3Dify) treat successful code execution as implicit proof of correctness. This is wrong for three reasons:

1. **A valid STEP file is not a dimensionally correct STEP file.** CadQuery can produce a geometrically valid solid that is 10× too large, oriented incorrectly, or missing critical features.
2. **Visually similar projections hide depth errors.** A front view that matches the drawing exactly can conceal an incorrect depth dimension or a missing pocket on the back face.
3. **An LLM that generated the model cannot reliably detect its own errors.** Confirmation bias in LLM self-evaluation is well-documented.

This system implements a three-layer validation stack:

```
Layer 1: CAD Kernel Checks    (deterministic — always run)
Layer 2: Dimensional Checks   (deterministic — run when OCR evidence available)
Layer 3: Projection Comparison (semi-deterministic — run when rendering succeeds)
```

Acceptance requires all three layers to pass their configured thresholds.

---

## 2. Layer 1 — CAD Kernel Checks

### 2.1 Checks Performed

Every candidate model undergoes the following checks after CadQuery construction:

| Check | Method | Pass Criterion | Failure Action |
|-------|--------|----------------|---------------|
| STEP export | `cadquery.exporters.export(shape, "STEP")` | No exception raised | `rejected` |
| STEP re-import | `importlib.import_module` + `cadquery.importers.importStep` | Shape is non-None | `rejected` |
| Solid count | `shape.solids().vals()` | ≥ 1 solid | `rejected` |
| Manifold check | `BRepCheck_Analyzer(shape).IsValid()` | True | `needs_review` |
| Open shell detection | `BRep_Builder` topology walk | No open shells | `needs_review` |
| Degenerate edges | Edge length check > 1e-6 mm | All edges valid | Warning |
| Bounding box non-zero | `shape.BoundingBox()` | All dims > 0.01 mm | `rejected` |
| Unit consistency | Metadata check | All dims in same unit | Warning |

### 2.2 Implementation

```python
# cad/validator.py
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
import cadquery as cq
from OCC.Core.BRepCheck import BRepCheck_Analyzer

@dataclass
class KernelReport:
    export_succeeded: bool
    reimport_succeeded: bool
    solid_count: int
    is_manifold: bool
    has_open_shells: bool
    bounding_box: dict  # {x_min, x_max, y_min, y_max, z_min, z_max, unit}
    volume_mm3: float
    surface_area_mm2: float
    degenerate_edge_count: int
    issues: list[str] = field(default_factory=list)

    @property
    def hard_pass(self) -> bool:
        """True only if no blocking errors exist."""
        return (
            self.export_succeeded
            and self.reimport_succeeded
            and self.solid_count >= 1
            and self.bounding_box["x_max"] > 0.01
        )

def validate_kernel(step_path: Path) -> KernelReport:
    """Run all kernel-level checks on a STEP file."""
    ...
```

### 2.3 What Kernel Checks Cannot Detect

- Incorrect absolute dimensions (a 100mm box vs. a 10mm box — both are valid)
- Missing features (a hole that should exist but doesn't)
- Incorrect feature placement (hole is 5mm off-center)
- Wrong material (outside scope of STEP geometry)

These require Layer 2 or Layer 3.

---

## 3. Layer 2 — Dimensional Checks

### 3.1 When This Layer Runs

Only when `DrawingEvidence` contains ≥ 1 extracted dimension with confidence ≥ 0.6.

If no dimensions were extracted, this layer is skipped and the fact is recorded in the validation report. The model cannot be marked `accepted` without at least one dimensional check; it receives `accepted_with_warnings` at best.

### 3.2 Checks Performed

| Check | Method | Tolerance |
|-------|--------|-----------|
| Overall width | STEP bounding-box X vs. extracted width | ±5% (configurable) |
| Overall height | STEP bounding-box Y vs. extracted height | ±5% |
| Overall depth | STEP bounding-box Z vs. extracted depth | ±10% (depth is least reliable) |
| Hole diameter | CadQuery face area → inferred diameter | ±5% |
| Feature spacing | Centroid distance between detected features | ±8% |

### 3.3 Dimensional Error Reporting

```python
@dataclass
class DimensionalError:
    dim_id: str
    description: str
    extracted_value: float
    extracted_unit: str
    model_value: float
    relative_error: float  # |model - extracted| / extracted
    within_tolerance: bool

@dataclass
class DimensionalReport:
    has_extracted_dims: bool
    errors: list[DimensionalError]
    
    @property
    def all_within_tolerance(self) -> bool:
        return all(e.within_tolerance for e in self.errors)

    @property
    def max_relative_error(self) -> float:
        return max((e.relative_error for e in self.errors), default=0.0)
```

### 3.4 Provenance Rule

Dimensions extracted by OCR from explicit annotations (e.g., "25.4 mm" with dimension arrow) are treated as **ground truth** for validation purposes.

Dimensions inferred by VLM visual estimation from pixel measurement are treated as **low-confidence estimates** and trigger a `needs_review` result rather than a hard `rejected`.

This distinction is preserved in `DrawingEvidence.extraction_method`.

---

## 4. Layer 3 — Projection Comparison

### 4.1 Rendering

The validated STEP is rendered to orthographic PNG images at a controlled scale:

```python
# cad/renderer.py
def render_orthographic_views(
    step_path: Path,
    output_dir: Path,
    views: list[str] = ["front", "top", "right"],
    resolution: tuple[int, int] = (1024, 1024),
) -> dict[str, Path]:
    """Render STEP file to orthographic PNG views."""
    ...
```

Scale is matched to the drawing's detected scale factor when known; otherwise normalized to bounding-box fill.

### 4.2 Comparison Metrics

All metrics are computed per detected orthographic view.

#### IoU (Intersection over Union)
```
IoU = |A ∩ B| / |A ∪ B|
```
Where A = silhouette mask from drawing, B = silhouette mask from rendered STEP.

- **Pass threshold:** IoU ≥ 0.75 (configurable)
- **Warning threshold:** 0.60 ≤ IoU < 0.75
- **Fail threshold:** IoU < 0.60

#### Edge Map Similarity
Canny edge detection applied to both images after normalization. F1 score between edge pixels within 3px tolerance.

- **Pass threshold:** Edge F1 ≥ 0.65

#### Contour Hausdorff Distance
95th-percentile Hausdorff distance between outer contour point sets, normalized by bounding box diagonal.

- **Pass threshold:** Normalized H95 ≤ 0.05

#### Per-View Summary Table

```python
@dataclass
class ViewComparison:
    view_type: str      # front | top | right | left | bottom | isometric
    iou: float
    edge_f1: float
    hausdorff_normalized: float
    diff_image_path: Path  # Side-by-side difference image saved for UI

@dataclass
class ComparisonReport:
    views: list[ViewComparison]
    overall_iou: float           # Average across available views
    overall_edge_f1: float
    rendering_succeeded: bool
    rendering_failure_reason: str | None
```

### 4.3 What Projection Comparison Cannot Detect

This is explicitly documented in every validation report:

> **Validation note:** 2D projection comparison confirms that visible outlines and edges align with the drawing. It cannot detect:
> - Incorrect depth dimensions (depth errors are invisible in front/top views if width/height match)
> - Internal features (pockets, blind holes, internal channels) that do not affect the silhouette
> - Incorrect feature placement within the silhouette boundary
> - Missing features on faces not visible in the compared views
>
> Full dimensional verification requires reference STEP models or physical measurement.

---

## 5. Acceptance Policy

### 5.1 Decision Matrix

```
kernel.hard_pass == False   →  status = "rejected"
dimensional.max_relative_error > HARD_DIM_THRESHOLD  →  status = "rejected"

kernel.is_manifold == False  →  status = "needs_review"
dimensional.has_extracted_dims == False  →  status = "accepted_with_warnings"
dimensional.all_within_tolerance == False  →  status = "needs_review"
comparison.overall_iou < WARN_IOU  →  status = "accepted_with_warnings"
comparison.overall_iou < FAIL_IOU  →  status = "needs_review"

All above pass  →  status = "accepted"
```

### 5.2 Default Thresholds (Configurable)

| Parameter | Default | Notes |
|-----------|---------|-------|
| `min_iou_accept` | 0.75 | IoU below this → warning |
| `min_iou_pass` | 0.60 | IoU below this → needs_review |
| `min_edge_f1` | 0.65 | |
| `max_hausdorff_norm` | 0.05 | |
| `max_dim_error_hard` | 0.20 | 20% error → rejected |
| `max_dim_error_warn` | 0.05 | 5% error → warning |

### 5.3 Calibration Status

> [!WARNING]
> These default thresholds are engineering estimates, NOT statistically calibrated. They must be validated against a held-out benchmark set with known-good reference models before being treated as reliable acceptance criteria. Until calibrated, classify these as **uncalibrated quality indicators**, not probability estimates.

---

## 6. Validation Report Structure

Every job produces a machine-readable validation report (`validation_report.json`):

```json
{
  "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "attempt_id": "...",
  "timestamp": "2026-10-10T01:00:00Z",
  "model_file": "artifacts/model.step",
  "kernel": {
    "export_succeeded": true,
    "reimport_succeeded": true,
    "solid_count": 1,
    "is_manifold": true,
    "has_open_shells": false,
    "bounding_box": {"x": 50.0, "y": 30.0, "z": 20.0, "unit": "mm"},
    "volume_mm3": 28500.0
  },
  "dimensional": {
    "has_extracted_dims": true,
    "errors": [
      {
        "dim_id": "width_front",
        "description": "Overall width from front view",
        "extracted_value": 50.0,
        "model_value": 49.8,
        "relative_error": 0.004,
        "within_tolerance": true
      }
    ]
  },
  "projection": {
    "views": [
      {"view": "front", "iou": 0.82, "edge_f1": 0.74, "hausdorff_norm": 0.031}
    ],
    "overall_iou": 0.82
  },
  "acceptance": {
    "status": "accepted",
    "issues": [],
    "calibration_note": "Thresholds are uncalibrated estimates. Verify against reference models."
  },
  "limitations": [
    "2D projection comparison cannot detect depth errors or internal features.",
    "1 dimension extracted; remaining dimensions are VLM estimates with unknown accuracy."
  ]
}
```

---

## 7. Human Review Integration

When `status = "needs_review"`, the job is surfaced in the review queue. A reviewer can:

1. Inspect the validation report and diff images
2. Approve: override status to `accepted` with reviewer ID and note
3. Reject: provide reason; case logged as verified failure
4. Correct: upload corrected STEP or enter corrected dimensions; both original and corrected versions preserved

Approved cases with corrections become candidates for the verified case library (after promotion, which requires explicit action — not automatic).
