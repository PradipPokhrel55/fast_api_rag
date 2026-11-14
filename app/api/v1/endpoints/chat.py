from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_chat_memory, get_rag_service
from app.db.session import get_db
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse
from app.services.rag_service import RagService
from app.services.redis_memory import ChatMemory

router = APIRouter(prefix="/chat", tags=["Conversational RAG"])


@router.post("", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    rag_service: RagService = Depends(get_rag_service),
) -> ChatResponse:
    return rag_service.handle_turn(db=db, session_id=request.session_id, message=request.message)


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
def get_chat_history(
    session_id: str,
    chat_memory: ChatMemory = Depends(get_chat_memory),
) -> ChatHistoryResponse:
    messages = chat_memory.get_history(session_id, max_turns=1000)
    return ChatHistoryResponse(session_id=session_id, messages=messages)
