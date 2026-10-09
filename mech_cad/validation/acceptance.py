"""Deterministic Acceptance Policy Subsystem."""

from dataclasses import dataclass, field
from typing import Literal
from mech_cad.cad.validator import KernelReport


@dataclass
class DimensionalReport:
    has_extracted_dims: bool = False
    max_relative_error: float = 0.0
    dim_issues: list[str] = field(default_factory=list)


@dataclass
class AcceptanceResult:
    status: Literal["accepted", "accepted_with_warnings", "needs_review", "rejected", "failed"]
    reasons: list[str] = field(default_factory=list)


def evaluate_acceptance(
    kernel: KernelReport,
    dimensional: DimensionalReport | None = None,
    max_dim_error_hard: float = 0.20,
    max_dim_error_warn: float = 0.05,
) -> AcceptanceResult:
    """Evaluate candidate 3D model deterministically based on validation metrics.
    
    Args:
        kernel: KernelReport from CAD kernel validation
        dimensional: Optional DimensionalReport
        max_dim_error_hard: Relative error threshold above which result is rejected (default 20%)
        max_dim_error_warn: Relative error threshold above which warning is added (default 5%)
        
    Returns:
        AcceptanceResult with status and detailed reasons
    """
    reasons = []

    # Hard kernel failures
    if not kernel.export_succeeded:
        return AcceptanceResult(status="rejected", reasons=["STEP file export failed"])
    if not kernel.reimport_succeeded:
        return AcceptanceResult(status="rejected", reasons=["STEP file re-import failed"])
    if kernel.solid_count < 1:
        return AcceptanceResult(status="rejected", reasons=["No solid body created in CAD model"])

    # Dimensional hard failures
    if dimensional and dimensional.has_extracted_dims:
        if dimensional.max_relative_error > max_dim_error_hard:
            return AcceptanceResult(
                status="rejected",
                reasons=[f"Dimensional error ({dimensional.max_relative_error:.1%}) exceeds hard limit ({max_dim_error_hard:.1%})"],
            )

    # Warnings / Needs Review
    if not kernel.is_manifold:
        reasons.append("Non-manifold B-rep topology detected.")
        return AcceptanceResult(status="needs_review", reasons=reasons)

    if dimensional and dimensional.has_extracted_dims:
        if dimensional.max_relative_error > max_dim_error_warn:
            reasons.append(f"Dimensional error ({dimensional.max_relative_error:.1%}) exceeds warning threshold.")
            return AcceptanceResult(status="accepted_with_warnings", reasons=reasons)
    else:
        reasons.append("No explicit dimensions were available for verification.")

    if kernel.issues:
        reasons.extend(kernel.issues)
        return AcceptanceResult(status="accepted_with_warnings", reasons=reasons)

    status = "accepted_with_warnings" if reasons else "accepted"
    return AcceptanceResult(status=status, reasons=reasons)
