from __future__ import annotations

from app.vector_store.chroma_client import get_feedback_collection


def retrieve_similar_feedback(embedding: list[float], n_results: int = 3) -> list[dict]:
    collection = get_feedback_collection()
    count = collection.count()
    if count == 0:
        return []

    results = collection.query(
        query_embeddings=[embedding],
        n_results=min(n_results, count),
        include=["documents", "metadatas", "distances"],
    )

    return [
        {"text": doc, "metadata": metadata, "distance": distance}
        for doc, metadata, distance in zip(
            results["documents"][0], results["metadatas"][0], results["distances"][0]
        )
    ]
