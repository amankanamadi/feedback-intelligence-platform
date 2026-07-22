from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection

from app.core.config import get_settings

FEEDBACK_COLLECTION_NAME = "feedback"


@lru_cache
def get_chroma_client() -> chromadb.ClientAPI:
    settings = get_settings()
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


@lru_cache
def get_feedback_collection() -> Collection:
    return get_chroma_client().get_or_create_collection(name=FEEDBACK_COLLECTION_NAME)
