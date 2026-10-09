"""Data structures for Extracted Drawing Evidence."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ExtractedDimension:
    dim_id: str
    label: str  # e.g., "width", "hole_diameter"
    value: float
    unit: Literal["mm", "in", "cm"] = "mm"
    source_view: str = "front"  # front | top | right | isometric
    confidence: float = 1.0     # 0.0 to 1.0
    extraction_method: Literal["ocr_explicit", "vlm_inferred", "manual_confirmed"] = "vlm_inferred"
    bounding_box_2d: list[int] = field(default_factory=list)  # [x1, y1, x2, y2]


@dataclass
class DetectedViewRegion:
    view_name: Literal["front", "top", "right", "left", "bottom", "isometric", "section"]
    crop_box: list[int]  # [left, top, right, bottom]
    confidence: float = 1.0


@dataclass
class DrawingEvidence:
    views: list[DetectedViewRegion] = field(default_factory=list)
    dimensions: list[ExtractedDimension] = field(default_factory=list)
    part_type_hypothesis: str = "prismatic"
    notes: list[str] = field(default_factory=list)
