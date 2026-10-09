"""Drawing Ingestion and Input Normalization Module."""

import io
from pathlib import Path
from dataclasses import dataclass
from PIL import Image, ImageOps
from mech_cad.config import settings

try:
    import magic
except ImportError:
    magic = None


class InputRejectedError(Exception):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


@dataclass
class NormalizedInput:
    file_path: Path
    mime_type: str
    width: int
    height: int
    size_bytes: int
    image: Image.Image


ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/bmp",
    "application/pdf",
}

MAX_IMAGE_DIMENSION = 10_000


def ingest_file(file_path: str | Path) -> NormalizedInput:
    """Safely validate and normalize input engineering drawing images or PDFs."""
    path = Path(file_path)
    if not path.exists():
        raise InputRejectedError(f"File not found: {path}", code="FILE_NOT_FOUND")

    size_bytes = path.stat().st_size
    if size_bytes > settings.MAX_UPLOAD_BYTES:
        raise InputRejectedError(
            f"File size ({size_bytes} bytes) exceeds limit ({settings.MAX_UPLOAD_BYTES} bytes)",
            code="FILE_TOO_LARGE",
        )

    mime = "application/octet-stream"
    if magic is not None:
        try:
            mime = magic.from_file(str(path), mime=True)
        except Exception:
            pass

    if mime == "application/octet-stream":
        ext = path.suffix.lower()
        if ext in [".jpg", ".jpeg"]:
            mime = "image/jpeg"
        elif ext == ".png":
            mime = "image/png"
        elif ext in [".tif", ".tiff"]:
            mime = "image/tiff"
        elif ext == ".bmp":
            mime = "image/bmp"
        elif ext == ".pdf":
            mime = "application/pdf"

    if mime not in ALLOWED_MIME_TYPES:
        raise InputRejectedError(
            f"Unsupported file format: {mime}. Allowed: {ALLOWED_MIME_TYPES}",
            code="UNSUPPORTED_TYPE",
        )

    if mime == "application/pdf":
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(str(path), first_page=1, last_page=1)
            if not pages:
                raise InputRejectedError("PDF contains no renderable pages", code="EMPTY_PDF")
            image = pages[0].convert("RGB")
        except Exception as e:
            raise InputRejectedError(f"Failed to extract image from PDF: {e}", code="PDF_CONVERSION_FAILED")
    else:
        try:
            image = Image.open(path)
            image.load()
            image = ImageOps.exif_transpose(image).convert("RGB")
        except Exception as e:
            raise InputRejectedError(f"Corrupt or invalid image file: {e}", code="INVALID_IMAGE")

    width, height = image.size
    if max(width, height) > MAX_IMAGE_DIMENSION:
        image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.Resampling.LANCZOS)
        width, height = image.size

    return NormalizedInput(
        file_path=path,
        mime_type=mime,
        width=width,
        height=height,
        size_bytes=size_bytes,
        image=image,
    )
