from fastapi import APIRouter, Query
import httpx

from config import settings

router = APIRouter(prefix="/api")


@router.get("/plans")
async def get_plans(
    zip_code: str = Query(default="78665"),
    estimated_use: int = Query(default=1000),
    plan_type: str = Query(default=""),
):
    payload = {
        "parameters": {
            "method": "plans",
            "zip_code": zip_code,
            "company_tdu_id": "",
            "company_unique_id": "",
            "plan_mo_from": "",
            "plan_mo_to": "",
            "estimated_use": estimated_use,
            "plan_type": plan_type,
            "rating_total": "",
            "include_details": True,
            "language": 0,
            "min_usage_plan": "off",
        }
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(settings.PTC_API_URL, json=payload)
        resp.raise_for_status()
        return resp.json()
