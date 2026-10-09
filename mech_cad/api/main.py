"""FastAPI REST Web Service and UI Handler."""

import asyncio
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select

from mech_cad.config import settings
from mech_cad.persistence.database import init_db, get_session
from mech_cad.persistence.models import Job, Artifact
from mech_cad.pipeline.orchestrator import run_pipeline

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise 2D Engineering Drawing to 3D CAD Conversion API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health_check():
    return {"status": "ok", "version": settings.VERSION, "project": settings.PROJECT_NAME}


@app.post("/jobs")
async def create_job(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Submit a 2D engineering drawing file for 3D CAD conversion."""
    temp_dir = settings.ARTIFACT_STORE_PATH / "uploads"
    temp_dir.mkdir(parents=True, exist_ok=True)
    input_file_path = temp_dir / file.filename

    with open(input_file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    job = Job(
        input_file_name=file.filename,
        mime_type=file.content_type or "application/octet-stream",
        status="queued",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Schedule pipeline execution
    background_tasks.add_task(asyncio.run, run_pipeline(job.id, input_file_path))

    return {"job_id": job.id, "status": job.status, "input_file_name": job.input_file_name}


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str, session: Session = Depends(get_session)):
    """Get status and details of a conversion job."""
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    artifacts = session.exec(select(Artifact).where(Artifact.job_id == job_id)).all()

    return {
        "job_id": job.id,
        "status": job.status,
        "acceptance_status": job.acceptance_status,
        "created_at": job.created_at,
        "error_message": job.error_message,
        "artifacts": [{"id": a.id, "type": a.artifact_type, "path": a.file_path} for a in artifacts],
    }


@app.get("/jobs/{job_id}/artifacts/{artifact_type}")
def download_artifact(job_id: str, artifact_type: str, session: Session = Depends(get_session)):
    """Download a generated CAD artifact (e.g. STEP)."""
    artifact = session.exec(
        select(Artifact).where(Artifact.job_id == job_id, Artifact.artifact_type == artifact_type)
    ).first()

    if not artifact or not Path(artifact.file_path).exists():
        raise HTTPException(status_code=404, detail="Artifact not found")

    return FileResponse(
        path=artifact.file_path,
        filename=Path(artifact.file_path).name,
        media_type="application/octet-stream",
    )


@app.get("/", response_class=HTMLResponse)
def index_ui():
    """Simple Web UI Dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MECH AI ADDON — 2D to 3D CAD</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0f172a; color: #e2e8f0; }
            h1 { color: #38bdf8; }
            .card { background: #1e293b; border-radius: 8px; padding: 24px; margin-top: 20px; border: 1px solid #334155; }
            input[type=file] { margin: 15px 0; }
            button { background: #0284c7; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }
            button:hover { background: #0369a1; }
            pre { background: #090d16; padding: 12px; border-radius: 6px; overflow-x: auto; }
            .status { font-weight: bold; color: #f59e0b; }
        </style>
    </head>
    <body>
        <h1>MECH AI ADDON</h1>
        <p>Enterprise-Grade 2D Engineering Drawing to 3D CAD System</p>
        
        <div class="card">
            <h3>Upload Engineering Drawing</h3>
            <form id="uploadForm">
                <input type="file" id="fileInput" accept="image/*,.pdf" required><br>
                <button type="submit">Convert to 3D STEP</button>
            </form>
        </div>

        <div class="card" id="statusCard" style="display:none;">
            <h3>Job Status</h3>
            <p>Job ID: <span id="jobIdDisplay">-</span></p>
            <p>Status: <span id="statusDisplay" class="status">Queued</span></p>
            <div id="downloadArea"></div>
        </div>

        <script>
            let currentJobId = null;
            document.getElementById('uploadForm').onsubmit = async (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('fileInput');
                if (!fileInput.files[0]) return;
                
                const formData = new FormData();
                formData.append('file', fileInput.files[0]);

                document.getElementById('statusCard').style.display = 'block';
                document.getElementById('statusDisplay').innerText = 'Uploading...';

                const res = await fetch('/jobs', { method: 'POST', body: formData });
                const data = await res.json();
                currentJobId = data.job_id;
                document.getElementById('jobIdDisplay').innerText = currentJobId;

                pollStatus();
            };

            async function pollStatus() {
                if (!currentJobId) return;
                const res = await fetch('/jobs/' + currentJobId);
                const data = await res.json();
                document.getElementById('statusDisplay').innerText = data.status + (data.acceptance_status ? ' (' + data.acceptance_status + ')' : '');

                if (data.status === 'completed' || data.status === 'needs_review') {
                    const stepArt = data.artifacts.find(a => a.type === 'step');
                    if (stepArt) {
                        document.getElementById('downloadArea').innerHTML = `<br><a href="/jobs/${currentJobId}/artifacts/step" download><button>Download STEP CAD File</button></a>`;
                    }
                } else if (data.status === 'failed') {
                    document.getElementById('downloadArea').innerHTML = `<p style="color:#ef4444;">Failed: ${data.error_message || 'Unknown error'}</p>`;
                } else {
                    setTimeout(pollStatus, 2000);
                }
            }
        </script>
    </body>
    </html>
    """
