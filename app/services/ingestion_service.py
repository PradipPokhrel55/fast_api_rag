from sqlalchemy.orm import Session

from app.core.exceptions import EmptyDocumentError
from app.db.models import Document
from app.schemas.document import DocumentUploadResponse
from app.services.chunking import ChunkingStrategy, get_chunker
from app.services.embeddings import EmbeddingClient
from app.services.text_extraction import extract_text
from app.services.vector_store import QdrantVectorStore


class IngestionService:
    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self._embedding_client = embedding_client or EmbeddingClient()
        self._vector_store = vector_store or QdrantVectorStore()

    def ingest(
        self,
        db: Session,
        filename: str,
        content: bytes,
        content_type: str,
        chunking_strategy: ChunkingStrategy,
    ) -> DocumentUploadResponse:
        text = extract_text(filename, content)
        if not text:
            raise EmptyDocumentError(f"No extractable text found in '{filename}'")

        chunker = get_chunker(chunking_strategy)
        chunks = chunker.chunk(text)
        if not chunks:
            raise EmptyDocumentError(f"Chunking produced no segments for '{filename}'")

        embeddings = self._embedding_client.embed_texts(chunks)
        self._vector_store.ensure_collection(vector_size=len(embeddings[0]))

        document = Document(
            filename=filename,
            content_type=content_type,
            chunking_strategy=chunking_strategy.value,
            chunk_count=len(chunks),
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        self._vector_store.upsert_chunks(
            document_id=document.id,
            chunks=chunks,
            embeddings=embeddings,
            chunking_strategy=chunking_strategy.value,
        )

        return DocumentUploadResponse(
            document_id=document.id,
            filename=filename,
            chunking_strategy=chunking_strategy,
            chunk_count=len(chunks),
        )
