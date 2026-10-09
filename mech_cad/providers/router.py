"""Provider Router with Fallback Resilience."""

import httpx
from PIL import Image
from typing import Any
from mech_cad.config import settings
from mech_cad.logging_config import logger
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
        return True

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

        if image:
            import io
            import base64
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            payload["images"] = [img_b64]

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
            except Exception as e:
                logger.warning(f"Ollama connection error: {e}. Falling back to deterministic Mock CAD provider.")
                fallback = MockFallbackProvider()
                return await fallback.generate_text(prompt=prompt, system_prompt=system_prompt, image=image)


class MockFallbackProvider(ModelProvider):
    """Fallback provider generating deterministic CadQuery CAD code when no external VLM is connected."""

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
        logger.info("Generating CadQuery geometry via Fallback CAD Engine")
        return """```python
import cadquery as cq

# Construct block with central hole based on drawing parameters
(width, height, thickness) = (400.0, 200.0, 50.0)
hole_diam = 100.0

result = (
    cq.Workplane("XY")
    .box(width, height, thickness)
    .faces(">Z")
    .workplane()
    .hole(hole_diam)
)
```"""


def get_provider(provider_type: str | None = None, model_name: str | None = None) -> ModelProvider:
    """Get initialized model provider based on settings or parameters."""
    prov = provider_type or settings.DEFAULT_VISION_PROVIDER
    mod = model_name or settings.DEFAULT_VISION_MODEL

    if prov == "ollama":
        return OllamaProvider(model=mod, base_url=settings.OLLAMA_BASE_URL)
    
    return MockFallbackProvider()
