"""Schema definitions for structured CAD Feature Plans."""

from typing import Literal
from pydantic import BaseModel, Field


class WorkplaneSpec(BaseModel):
    plane: Literal["XY", "YZ", "XZ", "front", "top", "right"] = "XY"
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)


class FeatureOperation(BaseModel):
    op_type: Literal[
        "box",
        "cylinder",
        "extrude",
        "revolve",
        "hole",
        "cbore_hole",
        "csink_hole",
        "fillet",
        "chamfer",
        "cut",
        "union",
        "pattern_linear",
        "pattern_polar",
    ]
    name: str = Field(..., description="Unique descriptive identifier for the feature step")
    parameters: dict[str, float | str | list[float] | list[tuple[float, float]]] = Field(
        default_factory=dict, description="Parameters specific to the operation"
    )
    workplane: WorkplaneSpec = Field(default_factory=WorkplaneSpec)


class FeaturePlan(BaseModel):
    title: str = "Parametric Part Feature Plan"
    unit: Literal["mm", "in", "cm"] = "mm"
    base_dimensions: dict[str, float] = Field(
        default_factory=dict, description="Expected bounding dimensions: width, height, depth"
    )
    operations: list[FeatureOperation] = Field(
        default_factory=list, description="Ordered list of CAD feature construction steps"
    )
    python_code_override: str | None = Field(
        default=None, description="Direct CadQuery code if generated from LLM fallback"
    )
