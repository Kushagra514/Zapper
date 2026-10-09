"""Unit tests for CAD Kernel STEP Validator."""

import pytest
from pathlib import Path
from mech_cad.cad.executor import execute_cad_code
from mech_cad.cad.validator import validate_step_file

try:
    import cadquery
    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False


@pytest.mark.skipif(not HAS_CADQUERY, reason="cadquery package not installed in environment")
def test_step_validator_valid_solid(tmp_path: Path):
    code = "import cadquery as cq\nresult = cq.Workplane('XY').box(20.0, 20.0, 10.0)\n"
    exec_res = execute_cad_code(code=code, output_dir=tmp_path)
    assert exec_res["success"] is True

    report = validate_step_file(exec_res["output_step_path"])
    assert report.export_succeeded is True
    assert report.reimport_succeeded is True
    assert report.solid_count >= 1
    assert report.bounding_box["x_len"] == 20.0
    assert report.hard_pass is True


def test_step_validator_missing_file():
    report = validate_step_file("non_existent_file.step")
    assert report.export_succeeded is False
    assert report.hard_pass is False
