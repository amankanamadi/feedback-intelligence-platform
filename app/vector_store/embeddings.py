from __future__ import annotations

import logging

from app.ai.client import describe_openai_error, get_openai_client

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-small"


def get_embedding(text: str) -> list[float]:
    client = get_openai_client()
    try:
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    except Exception as exc:
        logger.warning("OpenAI embedding request failed: %s", describe_openai_error(exc))
        raise
    return response.data[0].embedding
