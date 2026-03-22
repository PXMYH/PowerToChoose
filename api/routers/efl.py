from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from database.connection import create_job, get_job, get_plan_data
from tasks.process_efl import process_efl_task

router = APIRouter(prefix="/api/efl")


class ProcessEFLRequest(BaseModel):
    plan_id: str
    efl_url: str


@router.post("/process", status_code=202)
async def process_efl(request: ProcessEFLRequest, background_tasks: BackgroundTasks):
    job_id = await create_job(request.plan_id, request.efl_url)
    background_tasks.add_task(
        process_efl_task, job_id, request.plan_id, request.efl_url
    )
    return {"job_id": job_id, "status": "queued"}


@router.get("/status/{job_id}")
async def get_efl_status(job_id: str):
    job = await get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/results/{plan_id}")
async def get_efl_results(plan_id: str):
    plan = await get_plan_data(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No EFL data found for this plan")
    return plan
