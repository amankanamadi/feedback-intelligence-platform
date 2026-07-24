from functools import lru_cache

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from app.core.config import get_settings


@lru_cache
def get_openai_client() -> OpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env file before making AI calls."
        )
    return OpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
    )


def describe_openai_error(exc: Exception) -> str:
    """Categorize an OpenAI SDK exception for clear, distinguishable logging.

    The SDK already retries transient errors (rate limits, timeouts,
    connection issues, 5xx server errors) internally before raising - by
    the time an exception reaches this function, retries have already been
    exhausted, so this just names which category of failure ultimately won.
    """
    if isinstance(exc, APITimeoutError):
        return "request timed out (retries exhausted)"
    if isinstance(exc, APIConnectionError):
        return "network/connection failure (retries exhausted)"
    if isinstance(exc, RateLimitError):
        return "rate limit exceeded (retries exhausted)"
    if isinstance(exc, AuthenticationError):
        return "invalid or expired API credentials"
    if isinstance(exc, BadRequestError):
        code = getattr(exc, "code", None)
        if code is None and isinstance(getattr(exc, "body", None), dict):
            code = exc.body.get("error", {}).get("code")
        if code == "context_length_exceeded":
            return "input exceeded the model's context length"
        return f"invalid request ({code or 'bad request'})"
    if isinstance(exc, InternalServerError):
        return "OpenAI server error (retries exhausted)"
    return f"unexpected error ({type(exc).__name__})"
