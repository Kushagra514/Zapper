"""Base Model Provider Interface."""

from abc import ABC, abstractmethod
from typing import Any
from PIL import Image


class ModelProvider(ABC):
    """Unified interface for AI Vision-Language and LLM model providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass

    @property
    @abstractmethod
    def supports_vision(self) -> bool:
        """True if provider supports multimodal image inputs."""
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        image: Image.Image | None = None,
        temperature: float = 0.1,
    ) -> str:
        """Generate response text from prompt and optional image."""
        pass
