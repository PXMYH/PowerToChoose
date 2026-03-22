import instructor
import litellm

from config import settings


def get_llm_client():
    """Return an instructor-patched LiteLLM client for structured output extraction."""
    litellm.api_key = settings.OPENROUTER_API_KEY
    return instructor.from_litellm(litellm.completion)
