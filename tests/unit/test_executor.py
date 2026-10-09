"""Unit tests for sandboxed CAD code executor."""

import pytest
from pathlib import Path
from mech_cad.cad.executor import execute_cad_code

try:
    import cadquery
    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False


@pytest.mark.skipif(not HAS_CADQUERY, reason="cadquery package not installed in environment")
def test_sandboxed_executor_success(tmp_path: Path):
    code = """
import cadquery as cq
result = cq.Workplane("XY").box(10.0, 10.0, 10.0)
"""
    res = execute_cad_code(code=code, output_dir=tmp_path, timeout_seconds=10)
    assert res["success"] is True
    assert res["output_step_path"] is not None
    assert Path(res["output_step_path"]).exists()


def test_sandboxed_executor_syntax_error(tmp_path: Path):
    code = "invalid python code {{syntax error"
    res = execute_cad_code(code=code, output_dir=tmp_path, timeout_seconds=10)
    assert res["success"] is False
    assert res["returncode"] != 0
