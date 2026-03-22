from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from database.connection import create_job, get_all_plans, get_job, get_plan_data
from services.validator import cross_validate_with_ptc, validate_plan
from tasks.process_efl import process_efl_task

router = APIRouter(prefix="/api/efl")


class ProcessEFLRequest(BaseModel):
    plan_id: str
    efl_url: str


class BatchProcessRequest(BaseModel):
    plans: list[ProcessEFLRequest]


@router.get("/plans")
async def list_efl_plans():
    """List all extracted EFL plans with pricing tiers and charges."""
    plans = await get_all_plans()
    return {"plans": plans, "total": len(plans)}


@router.post("/process", status_code=202)
async def process_efl(request: ProcessEFLRequest, background_tasks: BackgroundTasks):
    job_id = await create_job(request.plan_id, request.efl_url)
    background_tasks.add_task(
        process_efl_task, job_id, request.plan_id, request.efl_url
    )
    return {"job_id": job_id, "status": "queued"}


@router.post("/process/batch", status_code=202)
async def process_efl_batch(
    request: BatchProcessRequest, background_tasks: BackgroundTasks
):
    """PIPE-03: Accept batch of plans for EFL processing."""
    jobs = []
    for plan in request.plans:
        job_id = await create_job(plan.plan_id, plan.efl_url)
        background_tasks.add_task(process_efl_task, job_id, plan.plan_id, plan.efl_url)
        jobs.append({"plan_id": plan.plan_id, "job_id": job_id, "status": "queued"})
    return {"jobs": jobs, "total": len(jobs)}


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


@router.get("/validate/{plan_id}")
async def validate_efl(plan_id: str):
    """VAL-02 + VAL-03: Sanity checks and confidence scoring."""
    plan = await get_plan_data(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No EFL data found for this plan")
    return validate_plan(plan, plan_id)


@router.get("/cross-validate/{plan_id}")
async def cross_validate_efl(plan_id: str, zip_code: str = Query(default="78665")):
    """VAL-01: Cross-validate extracted prices against PTC API."""
    plan = await get_plan_data(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No EFL data found for this plan")
    return await cross_validate_with_ptc(plan, plan_id, zip_code)
