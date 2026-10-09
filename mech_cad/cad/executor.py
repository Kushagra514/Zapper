"""Sandboxed execution module for untrusted generated Python CAD code."""

import os
import sys
import subprocess
from pathlib import Path
from mech_cad.config import settings
from mech_cad.logging_config import logger

try:
    import resource
except ImportError:
    resource = None


def _apply_resource_limits():
    """Apply Linux resource limits to child process prior to execution."""
    if resource is None:
        return
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (settings.CAD_EXEC_TIMEOUT_SECONDS, settings.CAD_EXEC_TIMEOUT_SECONDS))
        max_mem = 2 * 1024 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_mem, max_mem))
        max_fsize = 200 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_fsize, max_fsize))
        resource.setrlimit(resource.RLIMIT_NPROC, (8, 8))
    except Exception as e:
        logger.warning(f"Failed to set resource limits: {e}")


def execute_cad_code(
    code: str,
    output_dir: Path,
    output_step_name: str = "model.step",
    timeout_seconds: int | None = None,
) -> dict:
    """Run generated Python CadQuery code safely in a separate subprocess."""
    output_dir.mkdir(parents=True, exist_ok=True)
    script_path = output_dir / "generated_cad_script.py"
    step_output_path = output_dir / output_step_name

    full_code = code
    if "result.export" not in code and "exporters.export" not in code:
        full_code += f"\n\nimport cadquery as cq\nif 'result' in locals():\n    cq.exporters.export(result, '{step_output_path}')\n"

    script_path.write_text(full_code, encoding="utf-8")
    timeout = timeout_seconds or settings.CAD_EXEC_TIMEOUT_SECONDS

    # Use current python executable to inherit installed packages if needed
    cmd = [sys.executable, str(script_path)]
    env = dict(os.environ)

    logger.info(f"Executing CAD code sandbox in {output_dir}")
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout + 5,
            cwd=str(output_dir),
            env=env,
            preexec_fn=_apply_resource_limits if os.name == "posix" else None,
        )

        stdout = proc.stdout.decode("utf-8", errors="replace")[:50_000]
        stderr = proc.stderr.decode("utf-8", errors="replace")[:50_000]

        success = proc.returncode == 0 and step_output_path.exists()

        return {
            "success": success,
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "output_step_path": str(step_output_path) if step_output_path.exists() else None,
            "script_path": str(script_path),
        }
    except subprocess.TimeoutExpired:
        logger.error("CAD code execution timed out in sandbox")
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Execution timed out.",
            "output_step_path": None,
            "script_path": str(script_path),
        }
    except Exception as e:
        logger.error(f"Sandbox error executing CAD code: {e}")
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": str(e),
            "output_step_path": None,
            "script_path": str(script_path),
        }
