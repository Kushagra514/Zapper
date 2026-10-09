# Reference Repository Comparison

> **Date:** 2026-10-10  
> **Purpose:** Inform a unified target architecture for the MECH AI ADDON platform

---

## 1. Summary Comparison

| Dimension | CAD3Dify | Agent3Dify |
|-----------|----------|------------|
| **Architecture** | Single-pass pipeline with refinement loop | LangGraph supervisor + subagent hierarchy |
| **Primary abstraction** | Python function `generate_step_from_2d_cad_image` | LangGraph ReAct agent with tool calls |
| **Orchestration** | LangChain SequentialChain (v1, deprecated) | LangGraph (modern) |
| **Drawing interpretation** | Single LLM call with image + CadQuery examples | Optional Gemini preprocessing + Builder LLM |
| **CAD construction** | LLM generates CadQuery Python → execute | LLM fills Python template → execute |
| **Rendering** | CadQuery STEP → PNG via cadquery-ocp | Subagent executes and renders |
| **Comparison** | Render vs original via image feed to refiner LLM | IoU + edge-mask + LLM verifier |
| **Verification** | LLM visual judgment only | LLM + IoU + edge mask (still not geometric) |
| **Refinement** | Full code regeneration × N | Fix plan JSON → builder re-runs |
| **Job isolation** | None (shared paths, sync) | Per-job temp workspace directory |
| **Persistence** | None | None (temp dir deleted on exit) |
| **Security** | PythonREPLTool (unrestricted) | Subagent exec (unrestricted) |
| **Open-weight support** | Partial (Llama via Vertex AI) | No |
| **UI** | Streamlit (basic) | CLI + optional Streamlit |
| **License** | MIT | MIT |
| **Dependency manager** | Poetry | uv |
| **Python version** | ≥3.10 | ≥3.13 |

---

## 2. Drawing Interpretation

### CAD3Dify
- Encodes image as base64, passes to multimodal LLM
- No OCR, no dimension extraction
- LLM estimates all coordinates visually
- Few-shot CadQuery examples bias output toward fluent code, not accurate dimensions

### Agent3Dify
- **image_editor** (Gemini): `extract_outline` (cleanup), `extract_view` (crop orthographic view), `custom` (corrective)
- `extract_view` uses Gemini vision to detect and crop front/top/right views deterministically
- Cropped views passed to builder — improvement over CAD3Dify's single-image approach
- Still no OCR, no structured dimension table, no constraint solving

**Assessment:** Agent3Dify's view extraction is meaningfully better. The approach of providing separate cropped orthographic views to the builder reduces ambiguity. However, dimension values are still visual estimates. Both repos lack any principled multi-view 3D reconstruction.

---

## 3. CAD Construction

### CAD3Dify
- `cad_code_generator.py`: LLM with 6 hard-coded CadQuery few-shot examples
- Generates free-form Python string with `$output_filename` template variable
- Code parsed by regex from markdown fence
- No schema validation, no feature plan

### Agent3Dify
- `model_template.py`: Python template with `# === YOUR CODE HERE ===` comment
- Builder subagent reads template, fills it with CadQuery operations
- `builder/SKILL.md` guides the LLM on strategy and output format
- Still free-form code within the template; no structured feature plan

**Assessment:** Agent3Dify's template approach is marginally better (consistent scaffold), but both systems allow the LLM to generate arbitrary code. Neither enforces a structured feature plan that can be validated before execution.

---

## 4. Code Execution

### CAD3Dify
- `PythonREPLTool` (LangChain experimental) — runs code in the same process
- Fallback: `exec()` directly for LLaMA models
- No sandboxing, no resource limits, no timeout enforcement
- CRITICAL security risk

### Agent3Dify
- Subagent receives tool permission to execute files
- Implementation delegates to platform executor (deepagents)
- Same security profile — no container, no resource limits documented
- `ExecutionGuard` detects looping by hashing tool calls, not by security policy

**Assessment:** Neither repo provides safe code execution. Agent3Dify's use of subagents adds an abstraction layer but does not provide a security boundary.

---

## 5. Rendering and Comparison

### CAD3Dify
- `render.py`: CadQuery `exporters.export()` → STEP → OCC `TopoDS_Shape` → render PNG
- Rendered image passed to refiner LLM which compares visually
- No quantitative comparison metrics

### Agent3Dify
- `image_compare.py`: 
  - `iou()`: intersection-over-union of silhouette masks
  - `edge_mask()`: Canny edge detection comparison
  - `make_diff_board()`: side-by-side comparison image
- Verifier subagent reads comparison images, writes fix_plan.json
- Fix plan passed to builder on next iteration

**Assessment:** Agent3Dify's quantitative IoU + edge comparison is a genuine improvement. The `make_diff_board` visualization helps the verifier LLM. However, IoU of 2D silhouette projections does not catch:
- Incorrect depth dimensions
- Internal features (holes, pockets that don't affect silhouette)
- Incorrect feature placement within the silhouette boundary

---

## 6. Validation

### CAD3Dify
- None. If code executes without exception, result is treated as correct.

### Agent3Dify
- Visual comparison via IoU + edge mask
- Verifier LLM judgment
- `build_report.json` records what was built
- No kernel-level validation (B-rep topology, manifold check, STEP re-import)

**Assessment:** Neither repo performs independent geometric validation. A STEP file that passes visual comparison may contain:
- Non-manifold geometry
- Open shells
- Degenerate faces/edges
- Incorrect dimensions that don't affect the silhouette view

---

## 7. Agent Orchestration

### CAD3Dify
- Simple Python function calls in sequence
- `CadCodeGeneratorChain → execute → CadCodeRefinerChain × N → execute`
- No dynamic routing, no failure-mode branching

### Agent3Dify
- LangGraph ReAct supervisor with: image_editor, task (subagent dispatch)
- `ExecutionGuard`: detects stalled loops via MD5 hash of (subagent, inputs)
- Supervisor can loop: preprocess → build → verify → fix → build → verify
- Fixed `GraphRecursionError` as hard stop

**Assessment:** Agent3Dify's dynamic orchestration is significantly more sophisticated. The supervisor can adapt based on verification results. However, the stopping criterion (convergence by signature hash) is weak — it stops when tool calls repeat, not when geometry improves.

---

## 8. Model Provider Integration

### CAD3Dify
- `chat_models.py`: factory for GPT (OpenAI), Claude (Anthropic), Gemini (VertexAI), Llama (VertexAI)
- All require API keys; no local inference path
- No provider abstraction interface — each model type has different code paths

### Agent3Dify
- `config.py`: model strings in LangChain format (`openai:gpt-5`, `google_genai:gemini-3.1-pro-preview`)
- LangChain `init_chat_model()` provides the abstraction
- Defaults: GPT-5 (supervisor), Gemini 3.1 Pro (builder), Gemini 3 Flash (verifier), Gemini 3.1 Flash Image (image editor)
- No open-weight/local model path

**Assessment:** Agent3Dify's use of `init_chat_model()` with model strings is cleaner. However, both repos require paid cloud APIs. Neither supports Ollama or local llama.cpp.

---

## 9. Web Interface

### CAD3Dify
- `scripts/app.py`: Streamlit app (~40 lines)
- Upload image → select model → run → show rendered result
- No job history, no progress tracking, no validation report display

### Agent3Dify
- CLI primary (`cli.py`)
- Progress streaming via `ProgressReporter` for terminal
- No dedicated web UI; Streamlit not present

**Assessment:** Neither provides a web interface suitable for enterprise use. No job management, no persistent history, no reviewer workflow.

---

## 10. Security Assessment

| Risk | CAD3Dify | Agent3Dify |
|------|----------|------------|
| Unrestricted code execution | CRITICAL | CRITICAL |
| No input validation | HIGH | HIGH |
| API key in env (acceptable) | MEDIUM | MEDIUM |
| No output size limits | HIGH | HIGH |
| No network isolation | CRITICAL | CRITICAL |

---

## 11. Concurrency and Persistence

| Property | CAD3Dify | Agent3Dify |
|---------|----------|------------|
| Job isolation | None | Per-job temp dir |
| Concurrent jobs | Unsafe (shared paths) | Mostly safe (temp dir) |
| Job persistence | None | None |
| Recovery after crash | None | None |
| Audit trail | None | None |

---

## 12. Components Selected for Reuse, Rewriting, or Exclusion

| Component | Source | Decision | Reason |
|-----------|--------|----------|--------|
| CadQuery for solid modeling | Both | **Reuse** | Mature, MIT, proven |
| Per-job workspace isolation | Agent3Dify | **Refactor → durable** | Good isolation concept; needs DB-backed state |
| image_compare (IoU, edge) | Agent3Dify | **Reuse + extend** | Useful signal; extend with contour/dim comparison |
| Orthographic view cropping | Agent3Dify | **Reuse** | Deterministic, useful |
| LangGraph orchestration | Agent3Dify | **Reuse** | Modern, flexible |
| SKILL.md prompt structure | Agent3Dify | **Refactor** | Good structure; add OCR + constraint extraction |
| config.py model strings | Agent3Dify | **Refactor** | Add local/Ollama paths |
| PythonREPLTool execution | CAD3Dify | **Replace** | Critical security flaw |
| LangChain SequentialChain | CAD3Dify | **Exclude** | Deprecated |
| Streamlit UI | CAD3Dify | **Replace** | Too minimal; no job management |
| Raw code generation | Both | **Replace** | Replace with structured feature plan |
| Validation (none) | Both | **Add** | Critical missing capability |
| Dimension extraction (none) | Both | **Add** | Critical missing capability |
| Persistence (none) | Both | **Add** | Critical missing capability |

---

## 13. Architecture Decision: One Coherent System

We will **not** mechanically combine both repos. We will build one system that:

1. Takes the **workspace isolation pattern** from Agent3Dify and makes it durable (database-backed)
2. Takes the **view extraction tooling** from Agent3Dify and extends it with OCR + dimension parsing
3. Takes the **image comparison metrics** from Agent3Dify and adds kernel-level geometric validation
4. Takes the **CadQuery construction** from both and wraps it in a **sandboxed executor** + **structured feature plan**
5. Replaces the **LangChain v1 chains** with a clean FastAPI + SQLite/PostgreSQL pipeline backend
6. Adds a **web UI** with job management, progress display, and reviewer workflow
7. Provides a **provider abstraction** supporting both cloud APIs and local Ollama models

This results in one backend, one pipeline, one database, one UI — not a patchwork of both repos.
