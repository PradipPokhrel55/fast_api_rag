from functools import lru_cache

from app.services.embeddings import EmbeddingClient
from app.services.ingestion_service import IngestionService
from app.services.llm_client import LlmClient
from app.services.rag_service import RagService
from app.services.redis_memory import ChatMemory
from app.services.vector_store import QdrantVectorStore


@lru_cache
def get_embedding_client() -> EmbeddingClient:
    return EmbeddingClient()


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    return QdrantVectorStore()


@lru_cache
def get_llm_client() -> LlmClient:
    return LlmClient()


@lru_cache
def get_chat_memory() -> ChatMemory:
    return ChatMemory()


@lru_cache
def get_ingestion_service() -> IngestionService:
    return IngestionService(embedding_client=get_embedding_client(), vector_store=get_vector_store())


@lru_cache
def get_rag_service() -> RagService:
    return RagService(
        embedding_client=get_embedding_client(),
        vector_store=get_vector_store(),
        llm_client=get_llm_client(),
        chat_memory=get_chat_memory(),
    )
