from unittest.mock import MagicMock, patch

import pytest

from models.efl import EFLData
from services.efl_extractor import SYSTEM_PROMPT, ExtractionError, extract_efl_data

SAMPLE_EFL_DATA = EFLData(
    provider_name="Test Energy",
    plan_name="Basic Fixed 12",
    plan_type="fixed",
    contract_term_months=12,
    early_termination_fee=150.0,
    etf_conditions="$150 flat fee",
    renewable_energy_pct=100.0,
    price_kwh_500=0.158,
    price_kwh_1000=0.119,
    price_kwh_2000=0.099,
    base_charge_monthly=9.95,
    tdu_delivery_charge_per_kwh=0.04,
    tdu_fixed_charge_monthly=4.39,
)


@pytest.mark.asyncio
async def test_extract_success():
    mock_client = MagicMock(return_value=SAMPLE_EFL_DATA)

    with patch("services.efl_extractor.get_llm_client", return_value=mock_client):
        result = await extract_efl_data("Sample EFL text content here")

    assert isinstance(result, EFLData)
    assert result.provider_name == "Test Energy"
    assert result.plan_type == "fixed"
    assert result.price_kwh_1000 == 0.119
    mock_client.assert_called_once()


@pytest.mark.asyncio
async def test_extract_failure_raises_extraction_error():
    mock_client = MagicMock(side_effect=ValueError("LLM parse error"))

    with (
        patch("services.efl_extractor.get_llm_client", return_value=mock_client),
        pytest.raises(ExtractionError, match="EFL extraction failed"),
    ):
        await extract_efl_data("Bad EFL text")


@pytest.mark.asyncio
async def test_extract_retry_on_rate_limit():
    import litellm

    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise litellm.RateLimitError(
                message="Rate limited",
                model=kwargs.get("model", "test"),
                llm_provider="openrouter",
            )
        return SAMPLE_EFL_DATA

    mock_client = MagicMock(side_effect=side_effect)

    with patch("services.efl_extractor.get_llm_client", return_value=mock_client):
        result = await extract_efl_data("EFL text that triggers rate limits")

    assert isinstance(result, EFLData)
    assert call_count == 3


def test_system_prompt_covers_requirements():
    assert "TDU" in SYSTEM_PROMPT
    assert "500" in SYSTEM_PROMPT
    assert "1000" in SYSTEM_PROMPT
    assert "2000" in SYSTEM_PROMPT
    assert "fixed" in SYSTEM_PROMPT
    assert "variable" in SYSTEM_PROMPT
    assert "early_termination_fee" in SYSTEM_PROMPT
    assert "renewable_energy_pct" in SYSTEM_PROMPT
    assert "minimum_usage" in SYSTEM_PROMPT
    assert "base_charge_monthly" in SYSTEM_PROMPT
    assert "special_terms" in SYSTEM_PROMPT
