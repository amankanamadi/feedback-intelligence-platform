from __future__ import annotations

import logging
from typing import TypeVar

from pydantic import BaseModel

from app.ai.client import describe_openai_error, get_openai_client
from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredCompletionError(Exception):
    pass


def get_structured_completion(
    messages: list[dict[str, str]],
    response_model: type[T],
    model: str | None = None,
) -> T:
    """Call OpenAI's Structured Outputs and return a validated instance of
    `response_model`. The model's JSON schema is derived automatically from
    the Pydantic class and enforced by the API itself, not just checked
    after the fact.
    """
    client = get_openai_client()
    settings = get_settings()

    try:
        completion = client.beta.chat.completions.parse(
            model=model or settings.openai_model,
            messages=messages,
            response_format=response_model,
        )
    except Exception as exc:
        # Covers cases beyond a clean refusal/parsed=None: a response that
        # violates a Pydantic constraint the API's JSON schema doesn't
        # enforce (e.g. confidence out of range), truncated output, or any
        # other SDK-level failure. Standardizing on one error type here
        # means every caller's existing `except Exception` handling
        # continues to work unchanged.
        reason = describe_openai_error(exc)
        logger.warning("OpenAI structured completion failed: %s", reason)
        raise StructuredCompletionError(f"OpenAI structured completion failed: {reason}") from exc

    choice = completion.choices[0]
    if choice.message.refusal:
        raise StructuredCompletionError(f"Model refused to respond: {choice.message.refusal}")

    parsed = choice.message.parsed
    if parsed is None:
        raise StructuredCompletionError("Model response did not match the expected schema.")

    return parsed
