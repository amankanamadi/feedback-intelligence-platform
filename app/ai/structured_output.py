from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.ai.client import get_openai_client
from app.core.config import get_settings

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

    completion = client.beta.chat.completions.parse(
        model=model or settings.openai_model,
        messages=messages,
        response_format=response_model,
    )

    choice = completion.choices[0]
    if choice.message.refusal:
        raise StructuredCompletionError(f"Model refused to respond: {choice.message.refusal}")

    parsed = choice.message.parsed
    if parsed is None:
        raise StructuredCompletionError("Model response did not match the expected schema.")

    return parsed
