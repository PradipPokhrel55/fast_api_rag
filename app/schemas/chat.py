from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str | None = Field(default=None, description="Existing session id; a new one is created if omitted")
    message: str = Field(min_length=1, max_length=4000)


class RetrievedSource(BaseModel):
    document_id: str
    chunk_index: int
    score: float
    text: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    intent: str
    sources: list[RetrievedSource] = []
    booking_id: str | None = None


class ChatMessageSchema(BaseModel):
    role: str
    content: str
    timestamp: datetime


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[ChatMessageSchema]
