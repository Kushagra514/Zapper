"""Pipeline Data Transfer Schemas."""

from pathlib import Path
from pydantic import BaseModel
from mech_cad.cad.feature_plan import FeaturePlan
from mech_cad.cad.validator import KernelReport
from mech_cad.drawing.evidence import DrawingEvidence
from mech_cad.drawing.quality import QualityReport
from mech_cad.validation.acceptance import AcceptanceResult


class PipelineState(BaseModel):
    job_id: str
    input_path: Path
    output_dir: Path
    stage: str = "ingest"
    quality: QualityReport | None = None
    evidence: DrawingEvidence | None = None
    feature_plan: FeaturePlan | None = None
    generated_code: str | None = None
    step_path: Path | None = None
    kernel_report: KernelReport | None = None
    acceptance: AcceptanceResult | None = None
    error: str | None = None
