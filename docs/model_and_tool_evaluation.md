# Model and Tool Evaluation

> **Date:** 2026-10-10  
> **Status:** Initial evaluation — capability claims require benchmark validation  
> **Note:** All "free tier" claims reflect terms at audit date. Verify current terms before production deployment.

---

## 1. Vision-Language Models

### 1.1 Comparative Table

| Model | Provider | Free Path | Commercial License | Image Input | JSON Output | CadQuery Quality | Notes |
|-------|----------|-----------|-------------------|-------------|-------------|-----------------|-------|
| **GPT-4o** | OpenAI | No (paid only) | Yes (API ToS) | ✅ | ✅ | High | Best benchmark performance; ~\$5/1M tokens |
| **GPT-4o-mini** | OpenAI | No | Yes | ✅ | ✅ | Medium | Cheaper; may miss complex geometry |
| **Claude Sonnet 4.x** | Anthropic | No (paid only) | Yes | ✅ | ✅ | High | Excellent structured output |
| **Gemini 1.5 Flash** | Google | Free tier (rate-limited) | Verify ToS | ✅ | ✅ | Medium-High | 15 RPM free; suitable for dev |
| **Gemini 1.5 Pro** | Google | No (paid) | Yes | ✅ | ✅ | High | Best Google offering |
| **Gemini 2.0 Flash** | Google | Free tier | Verify ToS | ✅ | ✅ | Medium-High | Faster; lower quality on complex drawings |
| **LLaMA 3.2 Vision 11B** | Meta (open-weight) | Local/Ollama | Apache 2.0 | ✅ | Partial | Low-Medium | CPU-runnable on 16 GB; quality gap vs. paid |
| **LLaMA 3.2 Vision 90B** | Meta (open-weight) | Local/Ollama | Apache 2.0 | ✅ | Partial | Medium | Requires 64+ GB RAM or GPU |
| **Qwen2-VL 7B** | Alibaba (open-weight) | Local/Ollama | Qwen ToS (check) | ✅ | Partial | Low-Medium | Good diagram understanding; verify license |
| **LLaVA 1.6** | Open-source | Local/Ollama | Various | ✅ | Limited | Low | Older, weaker on engineering drawings |
| **Mistral 7B Instruct** | Mistral (open-weight) | Local/Ollama | Apache 2.0 | ❌ | ✅ | N/A (no vision) | Text-only; useful for planning/reasoning |

> [!WARNING]
> Do not assume open-weight = free commercial use. LLaMA models require Meta's license agreement. Qwen models have Alibaba-specific terms. Always verify before commercial deployment.

> [!NOTE]
> "Free tier" for Google Gemini at time of writing: 15 RPM, 1M tokens/day for Flash models. This may change. Rate limits make free tier unsuitable for production throughput.

### 1.2 Recommended Default Configuration

| Task | Default (No API Key) | Default (With Cloud API) | Rationale |
|------|---------------------|--------------------------|-----------|
| View extraction & understanding | LLaMA 3.2 Vision 11B (Ollama) | Gemini 1.5 Flash | Free, sufficient for view detection |
| Dimension OCR | Tesseract + PaddleOCR | Google Cloud Vision | Deterministic preferred |
| Feature planning | LLaMA 3.2 Vision 11B | GPT-4o or Gemini 1.5 Pro | Higher quality needed |
| CadQuery code generation | LLaMA 3.2 Vision 11B | GPT-4o or Claude Sonnet | Complex structured output |
| Verification reasoning | LLaMA 3.2 Vision 11B | Gemini 1.5 Flash | Cost efficiency acceptable |
| Embedding (retrieval) | all-MiniLM-L6-v2 (local) | text-embedding-3-small | Local first |

---

## 2. OCR Systems

| Tool | License | Local | Accuracy on Engineering Drawings | Notes |
|------|---------|-------|----------------------------------|-------|
| **Tesseract 5** | Apache 2.0 | ✅ | Medium | Good for clean text; struggles with dimension arrows |
| **PaddleOCR** | Apache 2.0 | ✅ | Medium-High | Better layout understanding; recommended |
| **EasyOCR** | Apache 2.0 | ✅ | Medium | Slower; supports more languages |
| **Google Cloud Vision** | Paid | No | High | Excellent; requires API key and network |
| **Azure Document Intelligence** | Paid | No | High | Best for structured engineering forms |

**Recommendation:** PaddleOCR as primary local OCR. Google Cloud Vision as optional enhancement when API is available.

---

## 3. CAD Kernels

| Tool | License | STEP Export | B-rep Topology | Python API | Notes |
|------|---------|------------|----------------|------------|-------|
| **CadQuery + OCCT** | Apache 2.0 + LGPL | ✅ | ✅ | ✅ | Primary choice; proven in reference repos |
| **Build123d** | Apache 2.0 | ✅ | ✅ | ✅ | Modern successor to CadQuery; compatible OCCT |
| **FreeCAD** | LGPL | ✅ | ✅ | ✅ | Heavier; harder to embed |
| **Open CASCADE** | LGPL | ✅ | ✅ | Python via pythonOCC | Low-level; no high-level parametric API |
| **Blender** | GPL | Limited | ❌ (mesh only) | ✅ | Mesh, not B-rep |

**Decision:** **CadQuery** is the primary kernel. It has the largest existing LLM training signal (many CadQuery examples online), a clean Python API, STEP/STL export, and MIT-compatible licensing for embedding.

Build123d is a credible migration target if CadQuery maintenance stalls — its API is intentionally similar.

---

## 4. Image Comparison

| Method | Measures | Limitations |
|--------|----------|-------------|
| **IoU (silhouette)** | Outline overlap | Misses interior features, depth errors |
| **Edge mask comparison** | Line/contour alignment | Sensitive to rendering noise |
| **SSIM** | Structural similarity | Affected by annotations, text |
| **Chamfer distance (contours)** | Point-set distance on outlines | More robust than pixel IoU |
| **Hausdorff distance** | Maximum contour deviation | Captures worst-case misalignment |
| **Dimension endpoint matching** | Physical length accuracy | Requires detected dimensions |
| **3D shape metrics (after GT available)** | Chamfer distance 3D, volume error | Requires reference STEP |

**Recommendation:** Use IoU + edge mask as fast checks; add Chamfer distance on 2D contours for better comparison. Add 3D metrics when reference STEP becomes available.

---

## 5. Embedding Models (for Case Retrieval)

| Model | Size | Local | License | Notes |
|-------|------|-------|---------|-------|
| **all-MiniLM-L6-v2** | 80 MB | ✅ | Apache 2.0 | Fast; good for text features |
| **all-mpnet-base-v2** | 420 MB | ✅ | Apache 2.0 | Higher quality |
| **text-embedding-3-small** | API | No | OpenAI ToS | Best for cloud deployments |
| **CLIP ViT-B/32** | 350 MB | ✅ | MIT | Image + text embeddings |

**Recommendation:** `all-MiniLM-L6-v2` for text metadata retrieval. CLIP for image-based similarity (secondary, not primary retrieval).

---

## 6. Rendering

| Tool | License | Views | Quality | Notes |
|------|---------|-------|---------|-------|
| **CadQuery exporters** | Apache 2.0 | Basic | Medium | Already in stack |
| **pythonOCC + VTK** | LGPL | Flexible | High | Complex setup |
| **three.js (browser)** | MIT | Full 3D | High | Used for UI preview |
| **Open3D** | MIT | Multiple | High | Good for mesh analysis |

**Decision:** CadQuery rendering for pipeline validation. three.js (via GLB export) for browser preview.

---

## 7. Local Inference Stack

### 7.1 Recommended: Ollama

```bash
# Install
curl -fsSL https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama3.2-vision:11b   # Vision, 11B params, ~8 GB VRAM or 16 GB RAM
ollama pull qwen2.5-coder:7b      # Code generation without vision
ollama pull mistral:7b             # Text reasoning

# Serve
ollama serve  # Default port 11434
```

**Compatibility:** OpenAI-compatible API (`/v1/chat/completions`). Integrates directly with LangChain's `ChatOpenAI` via base_url override.

### 7.2 Hardware Requirements

| Configuration | Min RAM | Expected Quality | Expected Latency |
|---------------|---------|-----------------|-----------------|
| LLaMA 3.2 Vision 11B, CPU | 16 GB | Low-Medium | 60-300s/response |
| LLaMA 3.2 Vision 11B, GPU 8GB | 8 GB VRAM | Low-Medium | 10-30s/response |
| Gemini Flash free tier | N/A (cloud) | Medium-High | 5-20s/response |
| GPT-4o | N/A (cloud) | High | 10-30s/response |

> [!IMPORTANT]
> Quality gap between local and cloud models on engineering drawings is **significant**. Local 11B models often fail to extract correct dimensions or generate valid CadQuery for parts with more than 5 features. Always benchmark before claiming local-model equivalence.

---

## 8. Dependency Summary (Recommended Stack)

```toml
[project]
requires-python = ">=3.11"

dependencies = [
    # Core AI
    "langchain>=0.3",
    "langchain-openai>=0.2",
    "langchain-google-genai>=2.0",
    "langchain-community>=0.3",  # Ollama support
    "langgraph>=0.2",

    # CAD
    "cadquery>=2.4",
    "trimesh>=4.0",      # GLB/STL processing
    "numpy>=1.26",

    # Computer Vision
    "opencv-python-headless>=4.10",
    "Pillow>=10.0",
    "paddleocr>=2.8",    # Local OCR

    # Embedding / Retrieval
    "sentence-transformers>=3.0",
    "faiss-cpu>=1.8",    # Vector search

    # Web / API
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlmodel>=0.0.22",  # SQLite dev / PostgreSQL prod

    # Task queue
    "rq>=1.16",          # Redis Queue for workers
    "redis>=5.0",

    # Utilities
    "python-multipart>=0.0.12",  # File upload
    "pdf2image>=1.17",           # PDF extraction
    "loguru>=0.7",
    "pydantic>=2.8",
    "httpx>=0.27",
]
```

> [!NOTE]
> `paddleocr` requires additional system libraries (`libgomp`, `libGL`). Document OS setup steps in deployment guide.
