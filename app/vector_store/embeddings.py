from __future__ import annotations

from app.ai.client import get_openai_client
from app.vector_store.chroma_client import get_feedback_collection

EMBEDDING_MODEL = "text-embedding-3-small"


def get_embedding(text: str) -> list[float]:
    client = get_openai_client()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding


def store_feedback_embedding(
    feedback_id: int, text: str, metadata: dict[str, str] | None = None
) -> None:
    embedding = get_embedding(text)
    collection = get_feedback_collection()
    collection.upsert(
        ids=[str(feedback_id)],
        embeddings=[embedding],
        documents=[text],
        metadatas=[metadata or {}],
    )
