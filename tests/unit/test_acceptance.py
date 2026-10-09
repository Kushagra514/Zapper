"""Unit tests for Acceptance Policy."""

from mech_cad.cad.validator import KernelReport
from mech_cad.validation.acceptance import evaluate_acceptance, DimensionalReport


def test_acceptance_policy_pass():
    kernel = KernelReport(
        export_succeeded=True,
        reimport_succeeded=True,
        solid_count=1,
        is_manifold=True,
        bounding_box={"x_len": 10.0},
    )
    dim = DimensionalReport(has_extracted_dims=True, max_relative_error=0.02)
    res = evaluate_acceptance(kernel, dim)
    assert res.status == "accepted"


def test_acceptance_policy_rejection():
    kernel = KernelReport(export_succeeded=False)
    res = evaluate_acceptance(kernel)
    assert res.status == "rejected"
