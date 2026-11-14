import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import get_settings

settings = get_settings()


@dataclass(slots=True)
class RetrievedChunk:
    document_id: str
    chunk_index: int
    text: str
    score: float


def _build_client() -> QdrantClient:
    if settings.qdrant_local_path:
        return QdrantClient(path=settings.qdrant_local_path)
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


class QdrantVectorStore:
    def __init__(self, client: QdrantClient | None = None, collection_name: str | None = None) -> None:
        self._client = client or _build_client()
        self._collection_name = collection_name or settings.qdrant_collection_name

    def ensure_collection(self, vector_size: int) -> None:
        existing = {c.name for c in self._client.get_collections().collections}
        if self._collection_name in existing:
            return
        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=qdrant_models.VectorParams(size=vector_size, distance=qdrant_models.Distance.COSINE),
        )

    def upsert_chunks(
        self,
        document_id: str,
        chunks: list[str],
        embeddings: list[list[float]],
        chunking_strategy: str,
    ) -> None:
        points = [
            qdrant_models.PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "chunk_index": index,
                    "text": chunk_text,
                    "chunking_strategy": chunking_strategy,
                },
            )
            for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        self._client.upsert(collection_name=self._collection_name, points=points)

    def search(
        self,
        query_vector: list[float],
        top_k: int,
        document_id: str | None = None,
    ) -> list[RetrievedChunk]:
        if not self._collection_exists():
            return []

        query_filter = None
        if document_id:
            query_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="document_id", match=qdrant_models.MatchValue(value=document_id)
                    )
                ]
            )

        results = self._client.query_points(
            collection_name=self._collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=query_filter,
        ).points

        return [
            RetrievedChunk(
                document_id=point.payload["document_id"],
                chunk_index=point.payload["chunk_index"],
                text=point.payload["text"],
                score=point.score,
            )
            for point in results
        ]

    def _collection_exists(self) -> bool:
        existing = {c.name for c in self._client.get_collections().collections}
        return self._collection_name in existing
