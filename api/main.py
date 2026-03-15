from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PTC_URL = "https://www.powertochoose.org/en-us/service/v1/"


@app.get("/api/plans")
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
        resp = await client.post(PTC_URL, json=payload)
        resp.raise_for_status()
        return resp.json()
