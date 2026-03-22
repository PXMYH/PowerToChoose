import asyncio
import logging

import litellm
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import settings
from models.efl import EFLData
from services.llm_client import get_llm_client

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert at parsing Texas Electricity Facts Labels (EFLs).
Extract all pricing, charges, contract, and provider details from the document.

Key instructions:
- Prices at 500/1000/2000 kWh usage levels are typically shown in cents per kWh. Convert to dollars per kWh (divide by 100) if the document shows cents.
- TDU (Transmission/Distribution Utility) delivery charges MUST be separated from provider energy charges. TDU charges are pass-through regulated fees, not set by the provider.
- If a field is not present in the document, return null for that field.
- plan_type is "fixed" if the rate is locked for the contract term, "variable" if the rate can change.
- For early_termination_fee, extract the dollar amount. For etf_conditions, describe any conditions (e.g., "$15 per remaining month", "flat fee", "waived if moving").
- renewable_energy_pct should be a number between 0 and 100.
- base_charge_monthly is the fixed monthly fee charged by the provider (not TDU).
- tdu_delivery_charge_per_kwh is the per-kWh TDU delivery charge.
- tdu_fixed_charge_monthly is the fixed monthly TDU charge.
- minimum_usage_charge is any penalty for using below a threshold.
- minimum_usage_threshold_kwh is the kWh threshold below which the penalty applies.
- special_terms should capture any bill credits, promotions, autopay discounts, or other notable terms."""


class ExtractionError(Exception):
    pass


@retry(
    retry=retry_if_exception_type((litellm.RateLimitError,)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(settings.LLM_MAX_RETRIES),
    reraise=True,
)
def _call_llm(efl_text: str) -> EFLData:
    client = get_llm_client()
    return client.chat.completions.create(
        model=settings.LLM_MODEL,
        response_model=EFLData,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Extract structured data from this EFL document:\n\n{efl_text}",
            },
        ],
        timeout=settings.LLM_TIMEOUT,
    )


async def extract_efl_data(efl_text: str) -> EFLData:
    """Send EFL text to LLM and return validated EFLData."""
    try:
        result = await asyncio.to_thread(_call_llm, efl_text)
        return result
    except Exception as e:
        raise ExtractionError(f"EFL extraction failed: {e}") from e
