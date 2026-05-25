"""Token utilities — handles token estimation locally and accurate counts via Gemini API."""
import logging
from typing import Optional
from google.genai import Client

logger = logging.getLogger(__name__)


def estimate_tokens_local(text: str) -> int:
    """
    Estimates tokens locally using a robust character and word-based heuristic.
    This runs synchronously in O(1) time without blocking on API network latency.
    """
    if not text or not isinstance(text, str):
        return 0

    # 4 characters per token is a standard standard LLM heuristic.
    char_estimate = len(text) // 4

    # Standard English text averages 1.3 tokens per word.
    word_count = len(text.split())
    word_estimate = int(word_count * 1.3)

    # Return the average of the two heuristics for standard resume profiles
    return max(1, (char_estimate + word_estimate) // 2)


def count_tokens_api(client: Client, model: str, text: str) -> Optional[int]:
    """
    Counts exact tokens using Google Gemini's count_tokens API.
    Fails gracefully and falls back to local estimation if the API call times out or throws error.
    """
    if not client or not text:
        return estimate_tokens_local(text)

    try:
        response = client.models.count_tokens(
            model=model,
            contents=text
        )
        if response and hasattr(response, "total_tokens"):
            return response.total_tokens
    except Exception as e:
        logger.warning(f"Failed to fetch accurate token count from Gemini API: {e}. Falling back to local estimation.")

    return estimate_tokens_local(text)
