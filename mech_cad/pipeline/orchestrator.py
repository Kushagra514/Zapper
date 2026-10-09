"""Core 2D Drawing to 3D CAD Pipeline Orchestrator."""

import json
from pathlib import Path
from loguru import logger
from sqlmodel import Session

from mech_cad.cad.executor import execute_cad_code
from mech_cad.cad.validator import validate_step_file
from mech_cad.config import settings
from mech_cad.drawing.ingestion import ingest_file
from mech_cad.drawing.quality import assess_quality
from mech_cad.pipeline.schemas import PipelineState
from mech_cad.providers.router import get_provider
from mech_cad.persistence.database import engine
from mech_cad.persistence.models import Job, Attempt, Artifact
from mech_cad.validation.acceptance import evaluate_acceptance


async def run_pipeline(job_id: str, input_path: str | Path) -> PipelineState:
    """Run full 2D to 3D CAD conversion pipeline for a given job.
    
    Args:
        job_id: Unique job UUID
        input_path: Path to target drawing file
        
    Returns:
        Final PipelineState object
    """
    job_dir = settings.ARTIFACT_STORE_PATH / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    state = PipelineState(
        job_id=job_id,
        input_path=Path(input_path),
        output_dir=job_dir,
    )

    with Session(engine) as session:
        job = session.get(Job, job_id)
        if job:
            job.status = "running"
            session.add(job)
            session.commit()

        attempt = Attempt(job_id=job_id, stage_reached="ingest")
        session.add(attempt)
        session.commit()
        attempt_id = attempt.id

    try:
        # Stage 1: Ingest & Quality
        logger.info(f"[{job_id}] Stage 1: Ingesting file {input_path}")
        norm = ingest_file(input_path)
        state.quality = assess_quality(norm.image)
        state.stage = "quality_assessed"

        # Stage 2: Prompting Provider for CAD Generation
        logger.info(f"[{job_id}] Stage 2: Planning and generating CadQuery code")
        provider = get_provider()
        prompt = (
            "Analyze this 2D engineering drawing. Generate valid Python CadQuery code to construct "
            "the 3D CAD model. Output ONLY Python code inside a ```python ``` code block. "
            "Store the final solid in a variable named `result`."
        )
        code_resp = await provider.generate_text(prompt=prompt, image=norm.image)

        # Parse code block
        code = code_resp
        if "```python" in code_resp:
            code = code_resp.split("```python")[1].split("```")[0].strip()
        elif "```" in code_resp:
            code = code_resp.split("```")[1].split("```")[0].strip()

        state.generated_code = code
        state.stage = "code_generated"

        # Save generated script artifact
        script_file = job_dir / "model.py"
        script_file.write_text(code, encoding="utf-8")

        # Stage 3: Sandboxed CAD Execution
        logger.info(f"[{job_id}] Stage 3: Executing CadQuery code in sandbox")
        exec_res = execute_cad_code(code=code, output_dir=job_dir, output_step_name="model.step")

        if not exec_res["success"]:
            state.error = f"CAD Execution failed: {exec_res['stderr']}"
            state.stage = "execution_failed"
            logger.error(f"[{job_id}] Execution failed: {exec_res['stderr']}")
        else:
            state.step_path = Path(exec_res["output_step_path"])
            state.stage = "cad_constructed"

        # Stage 4: Kernel Validation
        if state.step_path:
            logger.info(f"[{job_id}] Stage 4: Kernel validation on STEP output")
            state.kernel_report = validate_step_file(state.step_path)
            state.acceptance = evaluate_acceptance(state.kernel_report)
            state.stage = "validated"

        # Record artifacts & update Job state
        with Session(engine) as session:
            job = session.get(Job, job_id)
            attempt = session.get(Attempt, attempt_id)

            if attempt:
                attempt.stage_reached = state.stage
                attempt.code_generated = state.generated_code
                attempt.status = "completed" if (state.acceptance and state.acceptance.status != "rejected") else "failed"
                session.add(attempt)

            if state.step_path and state.step_path.exists():
                art = Artifact(
                    job_id=job_id,
                    attempt_id=attempt_id,
                    artifact_type="step",
                    file_path=str(state.step_path),
                    size_bytes=state.step_path.stat().st_size,
                )
                session.add(art)

            if job:
                job.status = "completed" if (state.acceptance and state.acceptance.status in ["accepted", "accepted_with_warnings"]) else ("needs_review" if state.acceptance else "failed")
                job.acceptance_status = state.acceptance.status if state.acceptance else "failed"
                job.error_message = state.error
                session.add(job)

            session.commit()

        logger.info(f"[{job_id}] Pipeline completed with state: {state.stage}")

    except Exception as e:
        logger.exception(f"[{job_id}] Pipeline error: {e}")
        state.error = str(e)
        state.stage = "failed"
        with Session(engine) as session:
            job = session.get(Job, job_id)
            if job:
                job.status = "failed"
                job.error_message = str(e)
                session.add(job)
                session.commit()

    return state
