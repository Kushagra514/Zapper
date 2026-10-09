# Architecture Audit

> **Audit date:** 2026-10-10  
> **Auditor:** Principal Software Architect / AI Systems Engineer  
> **Status:** Complete — based on source inspection of both reference repositories

---

## 1. Existing Workspace

The workspace at `/home/kushagra/Downloads/MECH AI ADDON` was **empty** at audit time (single directory, zero files). There is no existing implementation to preserve. We are building from a clean slate, informed by:

- **CAD3Dify** (`github.com/neka-nat/cad3dify`) — reference for drawing-to-CadQuery pipeline
- **Agent3Dify** (`github.com/neka-nat/agent3dify`) — reference for agent orchestration

---

## 2. CAD3Dify — Source Audit

### 2.1 File Inventory

```
cad3dify/
  __init__.py           # exports generate_step_from_2d_cad_image
  agents.py             # PythonREPLTool executor with LangChain AgentExecutor
  chat_models.py        # Multi-provider LLM factory (GPT, Claude, Gemini, Llama/Vertex)
  image.py              # ImageData loader (base64 encoding)
  pipeline.py           # Main orchestration: generate → refine × N → export
  render.py             # CadQuery STEP render to PNG via cadquery-ocp
  v1/
    cad_code_generator.py  # LangChain SequentialChain: image → CadQuery code
    cad_code_refiner.py    # LangChain chain: original + rendered → corrected code
scripts/
  app.py                # Streamlit UI (minimal)
  cli.py                # CLI entry point
```

### 2.2 Execution Path (Confirmed by Source)

```
1. User uploads image → ImageData.load_from_file() → base64 encode
2. CadCodeGeneratorChain:
   a. HumanMessagePromptTemplate with image + few-shot CadQuery examples
   b. Single LLM call → raw text with ```python ... ``` block
   c. regex _parse_code() → extract code string
3. Template.substitute(output_filename) → inject output path
4. execute_python_code():
   a. If model is LLaMA → direct exec()  [CRITICAL SECURITY FLAW]
   b. Otherwise → LangChain AgentExecutor with PythonREPLTool
      - Agent can freely modify filesystem, call subprocesses
5. render_and_export_image() → CadQuery STEP → PNG
6. CadCodeRefinerChain × N:
   a. Original image + rendered PNG + previous code → LLM → corrected code
   b. execute_python_code() again
7. Final STEP file written to output_filepath
```

### 2.3 Critical Findings

| # | Finding | Severity | Impact |
|---|---------|----------|--------|
| F1 | **Unrestricted code execution**: `PythonREPLTool` and direct `exec()` with no sandbox | CRITICAL | Arbitrary filesystem/network access from uploaded drawings |
| F2 | **LLM is sole judge of correctness**: No independent geometric validation | HIGH | Silently incorrect STEP files |
| F3 | **Shared output paths**: `output.step` is a hardcoded global path | HIGH | Concurrent jobs overwrite each other |
| F4 | **No job persistence**: Results exist only in-process | HIGH | No history, audit trail, or recovery |
| F5 | **No dimension extraction**: LLM hallucinates coordinates from pixel estimation | HIGH | Dimensional inaccuracy |
| F6 | **No CAD-kernel validation**: STEP not re-imported or topology-checked | HIGH | Invalid B-rep shipped as output |
| F7 | **No multi-view association**: Single image processed, depth inferred by LLM | HIGH | Incorrect 3D geometry |
| F8 | **Refinement is blind retry**: No error diagnosis or targeted correction | MEDIUM | Wastes tokens, may degrade quality |
| F9 | **Refinement uses raw pixel similarity**: No edge/contour/dimension comparison | MEDIUM | Misleading quality signal |
| F10 | **No structured feature plan**: LLM generates free-form code directly | MEDIUM | No traceability, hard to correct |
| F11 | **Mandatory paid API**: GPT-4o, Claude, Gemini-3 are required; no free-tier path | MEDIUM | Blocks development without API keys |
| F12 | **Sync execution on main process**: CAD generation blocks the web server | MEDIUM | Not suitable for multi-user deployment |
| F13 | **No error classification**: Exception message stored nowhere | LOW | No learning from failures |
| F14 | **LangChain SequentialChain (deprecated)**: Uses old LangChain v1 API | LOW | Maintenance burden |
| F15 | **Python 3.13 only**: Hard requirement in pyproject.toml | LOW | Deployment friction |

---

## 3. Agent3Dify — Source Audit

### 3.1 File Inventory

```
src/agent3dify/
  __init__.py
  __main__.py           # python -m agent3dify entry
  agent_factory.py      # LangGraph agent builder (supervisor + subagents)
  app.py                # Async runner with LangGraph event streaming
  cli.py                # CLI with argparse
  config.py             # AgentModels dataclass, env var readers
  execution_guard.py    # Loop detection (stall by signature hash comparison)
  image_compare.py      # IoU, edge-mask comparison, diff board
  image_editor.py       # Gemini image editing (extract_outline, extract_view, custom)
  progress.py           # ProgressReporter (event → terminal/stream)
  prompts.py            # SUPERVISOR_PROMPT, MAIN_USER_PROMPT, builder/verifier skill prompts
  workspace.py          # Per-job temp directory, path resolver
  tools.py              # crop_reference_view, preprocess_reference_image, compare_renders
  resources/
    skills/
      builder/SKILL.md  # CadQuery builder agent instructions
      verifier/SKILL.md # Render verifier agent instructions
    templates/
      model_template.py # CadQuery Python template for LLM to fill
```

### 3.2 Execution Path (Confirmed by Source)

```
1. CLI/app receives image path + config
2. prepare_local_workspace() → per-job temp directory
3. Workspace.copy_reference(image) → /input/reference.png
4. build_agent() → LangGraph react agent with tools:
   - image_editor (Gemini image edit/crop)
   - task (invoke cadquery-builder or render-verifier subagent)
5. Supervisor decides preprocessing:
   a. extract_outline → /preprocessed/outline_only.png
   b. extract_view (front/top/right) → /preprocessed/front_ref.png etc.
6. Supervisor delegates to cadquery-builder subagent:
   a. Builder reads /input/reference.png + preprocessed images
   b. Builder reads /review/fix_plan.json if available
   c. Builder generates /generated/model.py
   d. Builder executes model.py [STILL UNRESTRICTED]
   e. Builder exports artifacts/model.step + model.stl
   f. Builder writes artifacts/build_report.json
7. Optionally: render-verifier subagent:
   a. Reads rendered projections + ref images
   b. image_compare.iou() + edge_mask() comparison
   c. Writes review/compare_report.json + review/fix_plan.json
8. ExecutionGuard detects stale loops via hash of subagent calls
9. Supervisor decides to stop or re-invoke builder
10. Final answer with artifact paths
```

### 3.3 Critical Findings

| # | Finding | Severity | Impact |
|---|---------|----------|--------|
| F1 | **Unrestricted code execution**: Subagent executes generated Python with shell access | CRITICAL | Same as CAD3Dify — no isolation |
| F2 | **No CAD-kernel validation**: model.step not re-imported or topology-checked | HIGH | Invalid B-rep shipped |
| F3 | **No dimension extraction**: Builder LLM estimates all dimensions visually | HIGH | Dimensional inaccuracy |
| F4 | **Gemini image editor required**: extract_outline/extract_view require Gemini API | HIGH | No open-weight fallback |
| F5 | **No cross-view constraint solving**: Views processed independently | HIGH | Incorrect 3D reconstruction |
| F6 | **Comparison is image similarity only**: IoU of 2D silhouettes ≠ 3D accuracy | HIGH | Misleading correctness signal |
| F7 | **No persistent job database**: Workspace is temp dir, deleted on exit | HIGH | No history or learning |
| F8 | **Stall detection is signature-based**: Hash of tool calls, not geometric convergence | MEDIUM | Can loop or stop too early |
| F9 | **deepagents dependency**: Private library, version-pinned, minimal docs | MEDIUM | Maintenance risk |
| F10 | **No acceptance policy**: No formal pass/fail/needs-review classification | MEDIUM | Every output is implicitly "successful" |
| F11 | **No structured feature plan**: LLM fills a Python template directly | MEDIUM | No traceability |
| F12 | **Mandatory GPT-5 + Gemini**: Default models require paid API access | MEDIUM | Blocks offline development |
| F13 | **Streamlit-only UI**: No job history, no multi-user, no persistent state | LOW | Not enterprise-suitable |
| F14 | **Python 3.13 only**: Hard requirement | LOW | Deployment friction |

---

## 4. What Is Genuinely Functional

| Component | Assessment |
|-----------|-----------|
| CadQuery via CadQuery/OCCT | ✅ Works — proven library for B-rep solid modeling |
| LangChain/LangGraph orchestration | ✅ Works — functional agent framework |
| Gemini image editing | ✅ Works — if Gemini API key available |
| Image-to-base64 encoding | ✅ Works |
| render_and_export_image() | ✅ Works for simple parts |
| IoU / edge-mask comparison | ✅ Works as a rough signal |
| Per-job workspace isolation (Agent3Dify) | ✅ Partially works — temp dir is isolated |
| Progress streaming (Agent3Dify) | ✅ Works for terminal display |

---

## 5. What Is Prototyped But Not Production-Ready

| Component | Gap |
|-----------|-----|
| Code execution | No sandbox, no resource limits, no timeout |
| Refinement | No targeted correction — full regeneration on every iteration |
| Validation | No kernel check, no dimension verification |
| Persistence | No database, no job history |
| Concurrency | Shared paths, no queue |
| Security | Generated code runs as the application process |
| Learning | No failure recording, no case retrieval |
| Benchmarking | No benchmark suite, no baseline metrics |

---

## 6. Components Worth Retaining

| Component | Action | Reason |
|-----------|--------|--------|
| CadQuery kernel | **Retain** | Mature, well-documented, MIT licensed |
| Per-job temp workspace (Agent3Dify) | **Refactor** | Good isolation concept, needs durable persistence |
| image_compare.py IoU/edge | **Retain + extend** | Useful signal, add contour/dimension comparison |
| image_editor.py crop_view | **Retain** | Deterministic crop is useful |
| SKILL.md prompts | **Refactor** | Good structure, needs OCR + constraint extraction added |
| config.py AgentModels | **Refactor** | Good pattern, needs open-weight models + local inference |

## 7. Components To Replace or Remove

| Component | Action | Reason |
|-----------|--------|--------|
| PythonREPLTool / direct exec() | **Replace** | Security critical — use sandboxed executor |
| LangChain v1 SequentialChain | **Replace** | Deprecated API |
| CadCodeGeneratorChain (raw code gen) | **Replace** | Needs structured feature plan schema |
| Mandatory paid APIs only | **Replace** | Needs open-weight model paths |
| Streamlit-only UI | **Extend** | Needs job history, progress, review workflow |
| Hardcoded output paths | **Replace** | Needs per-job artifact namespacing |

---

## 8. Security Vulnerabilities

1. **Remote code execution**: Both repos use `PythonREPLTool` or `exec()` on LLM-generated code without sandboxing. An adversarial drawing image could trigger prompt injection leading to filesystem access, data exfiltration, or supply-chain attacks.

2. **No input size limits**: No validation of file size, image dimensions, or MIME type before processing.

3. **API keys in environment variables**: Acceptable pattern, but no rotation, no secret manager, no redaction from logs.

4. **No output size limits on CAD execution**: A generated model could trigger excessive memory or CPU use.

---

## 9. Confirmed Assumptions vs. Pending Experiments

| Item | Status |
|------|--------|
| Workspace is empty (no local code) | **Confirmed** |
| CAD3Dify pipeline.py execution path | **Confirmed from source** |
| Agent3Dify LangGraph agent structure | **Confirmed from source** |
| Both repos require paid APIs by default | **Confirmed from config.py** |
| No database or persistent storage in either repo | **Confirmed** |
| CadQuery can export valid STEP from simple parts | **Assumed true** — requires local test |
| IoU comparison meaningfully correlates with geometric accuracy | **Unverified** — needs benchmark |
| Open-weight models (Ollama/Llama) can generate CadQuery | **Unverified** — needs experiment |
