# Benchmarking

> **Date:** 2026-10-10  
> **Principle:** Accuracy is an engineering objective, not a marketing claim. Every benchmark result must include methodology, sample size, and limitations.

---

## 1. Why Benchmarking Is Required

Both reference repositories (CAD3Dify, Agent3Dify) contain no benchmark suite. They show a rendered example image and imply the system works. This is insufficient for engineering use because:

- A single successful example does not characterize performance on unfamiliar drawings
- Visual similarity in a rendered image does not imply dimensional accuracy
- Without a baseline, it is impossible to determine whether a change improved or degraded the system

This document defines the benchmark methodology, metric definitions, data requirements, and reporting format.

---

## 2. Benchmark Case Definition

Each benchmark case must contain:

| Field | Required | Description |
|-------|----------|-------------|
| `case_id` | Yes | Stable identifier |
| `drawing_path` | Yes | Path to 2D drawing image |
| `drawing_format` | Yes | jpeg/png/pdf |
| `part_family` | Yes | prismatic/cylindrical/complex/other |
| `difficulty` | Yes | easy/medium/hard |
| `drawing_quality` | Yes | clean/moderate/poor |
| `view_count` | Yes | Number of orthographic views present |
| `has_dimensions` | Yes | Whether explicit dimensions are annotated |
| `reference_step_path` | Conditional | Reference STEP (required for 3D metrics) |
| `known_dimensions` | Yes | Dict of labeled dimensions in mm |
| `known_features` | Yes | List of feature types (hole, fillet, slot, etc.) |
| `expected_volume_mm3` | Conditional | Required for volume metric |
| `notes` | No | Ambiguities, known issues, special conditions |

Cases **without** a reference STEP file may only be used for:
- Valid STEP rate measurement
- Projection similarity measurement
- Feature presence checks

Cases **with** a reference STEP file support all metrics.

---

## 3. Benchmark Categories

### Category A — Simple Prismatic (5+ cases)
- Single extrusion or simple multi-step profile
- ≤3 features (holes, chamfers, fillets)
- Clean drawing quality
- Explicit dimension annotations
- Expected: high success rate

### Category B — Cylindrical / Revolved (3+ cases)
- Shafts, bosses, flanges
- Diameter/radius annotations
- Multiple views with section possible
- Expected: moderate success rate

### Category C — Multi-Feature (3+ cases)
- ≥5 distinct features
- Patterns, slots, pockets
- Multiple orthographic views
- Expected: lower success rate

### Category D — Challenging Input (3+ cases)
- Low-resolution scans
- Skewed or noisy drawings
- Missing dimensions
- Dense annotation overlays
- Expected: system should gracefully degrade

### Category E — Invalid / Unsupported (2+ cases)
- Corrupt images, wrong file type
- Assembly drawings (unsupported)
- Expected: explicit rejection, not silent failure

---

## 4. Metric Definitions

### 4.1 Pipeline Completion Rate
```
PCR = completed_jobs / total_jobs
```
A job "completes" if it reaches Stage 12 (artifact export) without an infrastructure error.

### 4.2 Valid CAD Solid Rate
```
VCSR = jobs_with_valid_manifold_solid / completed_jobs
```
Requires: STEP export succeeded AND STEP re-import succeeded AND is_manifold AND solid_count ≥ 1.

### 4.3 Acceptance Rate
```
AR = accepted_jobs / completed_jobs
```
Where `accepted` = `accepted` or `accepted_with_warnings` from the acceptance policy.

### 4.4 Dimensional Error (requires reference STEP or explicit dimensions)
```
DE_i = |model_dim_i - reference_dim_i| / reference_dim_i
Mean_DE = mean(DE_i for all comparable dimensions)
Max_DE = max(DE_i)
```
Reported separately for each dimension type (width, height, depth, hole_diameter).

### 4.5 Volume Error (requires reference STEP)
```
VE = |model_volume - reference_volume| / reference_volume
```

### 4.6 Projection IoU (per view)
```
IoU_v = silhouette_overlap(rendered_v, drawing_v)
Mean_IoU = mean(IoU_v for all matched views)
```

### 4.7 Human Acceptance Rate (HAR)
Fraction of `completed_jobs` that a domain expert would accept as geometrically correct.
Requires human review of each case. Reported with reviewer count and inter-rater agreement.

### 4.8 Cost per Accepted Model
```
CPAM = total_api_cost_$ / accepted_jobs
```
Includes all VLM calls, OCR calls, retries, and refinement iterations.

### 4.9 Median and P95 Latency
Wall-clock time from job submission to final artifact availability.

---

## 5. Data Leakage Prevention

> [!IMPORTANT]
> Near-duplicate drawings (same part, different scan or annotation style) must be assigned to the **same split**. They must never appear in both the development set and the evaluation set.

Split rules:
- Split by **part family/design lineage**, not randomly by drawing
- A given physical part (identified by part number or geometry) belongs entirely to one split
- Development cases: used for prompt tuning, strategy selection, hyperparameter adjustment
- Evaluation cases: fixed set, never used to tune anything; results reported as-is
- If a case is used for development at any point, it is excluded from evaluation

The fixed evaluation set is declared in `tests/benchmark/eval_set.json` and is not modified without explicit documentation of the reason.

---

## 6. Baseline Measurement (Milestone 1)

Before any architectural improvements, measure:

1. Run the initial vertical slice (Milestone 1 pipeline) on all benchmark cases
2. Record all metrics above
3. Store results in `tests/benchmark/results/baseline_YYYYMMDD.json`
4. This baseline is the permanent reference point for all future comparisons

A new architectural component must show statistically meaningful improvement over baseline before being declared an improvement. Anecdotal evidence of "it looks better" is not sufficient.

---

## 7. Benchmark Report Format

### 7.1 Machine-Readable

```json
{
  "benchmark_id": "b001",
  "run_date": "2026-10-10T00:00:00Z",
  "system_version": "0.1.0",
  "model_config": {
    "planner": "ollama:llama3.2-vision:11b",
    "builder": "ollama:llama3.2-vision:11b",
    "verifier": "ollama:llama3.2-vision:11b"
  },
  "summary": {
    "total_cases": 16,
    "pipeline_completion_rate": 0.875,
    "valid_cad_solid_rate": 0.714,
    "acceptance_rate": 0.571,
    "mean_iou": 0.68,
    "mean_dimensional_error": 0.12,
    "median_latency_seconds": 187,
    "p95_latency_seconds": 412,
    "cost_per_accepted_model_usd": 0.0
  },
  "by_category": {
    "A_simple_prismatic": {
      "cases": 5, "valid_cad_rate": 0.8, "acceptance_rate": 0.8, "mean_iou": 0.79
    },
    "B_cylindrical": {
      "cases": 3, "valid_cad_rate": 0.667, "acceptance_rate": 0.333, "mean_iou": 0.61
    }
  },
  "per_case": [
    {
      "case_id": "A001",
      "part_family": "prismatic",
      "difficulty": "easy",
      "acceptance_status": "accepted",
      "iou_front": 0.84,
      "dimensional_errors": {"width": 0.02, "height": 0.03},
      "latency_seconds": 145,
      "failure_category": null
    }
  ],
  "limitations": [
    "Reference STEP files not available for 11/16 cases — 3D metrics omitted for those cases.",
    "Human acceptance rate not measured in this run.",
    "Sample size (16 cases) is insufficient for statistical significance in subcategory analysis."
  ]
}
```

### 7.2 Human-Readable Summary

Produced by `tests/benchmark/report.py`, printed to console and saved as Markdown. Key rule: **do not hide subcategory failures behind an aggregate success rate.**

Example bad reporting (PROHIBITED):
> "The system achieved 80% success."

Example good reporting (REQUIRED):
> "The system processed 16 cases. Valid CAD solid rate: 71% overall.  
> By category: Simple prismatic: 80% (4/5). Cylindrical: 67% (2/3). Multi-feature: 50% (1/2). Challenging input: 25% (1/4). Dimensional error (where measurable): mean 12%, max 34%.  
> Sample size is small — these results are directional, not statistically reliable."

---

## 8. Regression Suite

Every pull request that touches pipeline stages, prompts, model routing, or CAD construction must run:

```bash
python -m pytest tests/benchmark/regression_suite.py -v
```

The regression suite runs the development subset of benchmark cases (not the fixed evaluation set) and fails if:
- Valid CAD solid rate drops by more than 5 percentage points vs. stored baseline
- Any previously-passing case now fails with `rejected` status
- Median latency increases by more than 50%

Regression results are stored alongside the PR record. No merge without passing regression.

---

## 9. Benchmark Provenance

Each benchmark case records:
- Source of drawing (URL, scan provenance, synthetic generation)
- License (public domain, CC, synthetic — check before use)
- Whether the reference STEP was human-generated or machine-generated and verified
- Date added to benchmark set

No drawing is added to the benchmark without confirming its license permits use in this system's testing workflow.
