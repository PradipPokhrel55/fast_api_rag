from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.services.chunking import ChunkingStrategy


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunking_strategy: ChunkingStrategy
    chunk_count: int
    status: str = "ingested"


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    content_type: str
    chunking_strategy: str
    chunk_count: int
    created_at: datetime
