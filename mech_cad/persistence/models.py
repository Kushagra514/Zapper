"""Database ORM models using SQLModel."""

import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Job(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    status: str = Field(default="queued")  # queued | running | completed | failed | needs_review
    input_file_name: str
    mime_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    acceptance_status: Optional[str] = None
    error_message: Optional[str] = None


class Attempt(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    attempt_number: int = 1
    stage_reached: str = "ingest"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"
    failure_category: Optional[str] = None
    code_generated: Optional[str] = None


class Artifact(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="job.id", index=True)
    attempt_id: Optional[str] = Field(default=None, foreign_key="attempt.id")
    artifact_type: str  # input_drawing | step | stl | glb | report | render
    file_path: str
    size_bytes: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
