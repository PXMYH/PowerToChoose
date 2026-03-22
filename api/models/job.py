from enum import Enum

from pydantic import BaseModel


class JobStatus(str, Enum):
    queued = "queued"
    downloading = "downloading"
    extracting = "extracting"
    parsing = "parsing"
    storing = "storing"
    completed = "completed"
    failed = "failed"


class Job(BaseModel):
    id: str
    plan_id: str
    status: JobStatus
    error: str | None = None
    created_at: str
    updated_at: str
