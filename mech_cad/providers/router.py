"""Provider Router and Fallback Factory."""

import httpx
from PIL import Image
from loguru import logger
from mech_cad.config import settings
from mech_cad.providers.base import ModelProvider


class OllamaProvider(ModelProvider):
    def __init__(self, model: str = settings.DEFAULT_VISION_MODEL, base_url: str = settings.OLLAMA_BASE_URL):
        self._model = model
        self._base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return f"ollama:{self._model}"

    @property
    def supports_vision(self) -> bool:
        return "vision" in self._model.lower() or "llava" in self._model.lower()

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        image: Image.Image | None = None,
        temperature: float = 0.1,
    ) -> str:
        url = f"{self._base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system_prompt:
            payload["system"] = system_prompt

        if image and self.supports_vision:
            import io
            import base64
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            payload["images"] = [img_b64]

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
            except Exception as e:
                logger.error(f"Ollama provider request failed: {e}")
                raise RuntimeError(f"Ollama provider failed: {e}")


class MockFallbackProvider(ModelProvider):
    """Fallback provider when no external API or Ollama is available."""

    @property
    def name(self) -> str:
        return "mock_fallback"

    @property
    def supports_vision(self) -> bool:
        return True

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        image: Image.Image | None = None,
        temperature: float = 0.1,
    ) -> str:
        logger.info("Using mock fallback CAD provider")
        # Return a simple valid CadQuery box code template
        return """```python
import cadquery as cq

# Base box fallback
(width, height, thickness) = (50.0, 30.0, 15.0)
result = cq.Workplane("XY").box(width, height, thickness).faces(">Z").hole(10.0)
```"""


def get_provider(provider_type: str | None = None, model_name: str | None = None) -> ModelProvider:
    """Get initialized model provider based on settings or parameters."""
    prov = provider_type or settings.DEFAULT_VISION_PROVIDER
    mod = model_name or settings.DEFAULT_VISION_MODEL

    if prov == "ollama":
        return OllamaProvider(model=mod, base_url=settings.OLLAMA_BASE_URL)
    
    # Default to mock fallback if offline / unconfigured provider
    return MockFallbackProvider()
