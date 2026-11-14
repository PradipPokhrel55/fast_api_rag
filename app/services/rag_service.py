import uuid

from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas.chat import ChatResponse, RetrievedSource
from app.services.booking_service import BookingService
from app.services.embeddings import EmbeddingClient
from app.services.llm_client import LlmClient
from app.services.redis_memory import ChatMemory
from app.services.vector_store import QdrantVectorStore

settings = get_settings()

_RAG_SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions using only the provided context. "
    "If the context does not contain the answer, say you don't know. Be concise."
)

_BOOKING_INTENT_KEYWORDS = ("book", "interview", "schedule", "appointment", "reschedule")


class RagService:
    """Orchestrates a single chat turn: booking-slot filling or custom retrieval + generation."""

    def __init__(
        self,
        embedding_client: EmbeddingClient | None = None,
        vector_store: QdrantVectorStore | None = None,
        llm_client: LlmClient | None = None,
        chat_memory: ChatMemory | None = None,
    ) -> None:
        self._embedding_client = embedding_client or EmbeddingClient()
        self._vector_store = vector_store or QdrantVectorStore()
        self._llm_client = llm_client or LlmClient()
        self._chat_memory = chat_memory or ChatMemory()

    def handle_turn(self, db: Session, session_id: str | None, message: str) -> ChatResponse:
        session_id = session_id or str(uuid.uuid4())
        self._chat_memory.add_message(session_id, "user", message)

        booking_state = self._chat_memory.get_booking_state(session_id)
        booking_in_progress = booking_state is not None
        looks_like_booking = booking_in_progress or _mentions_booking_intent(message)

        if looks_like_booking:
            response = self._handle_booking_turn(db, session_id, message, booking_state or {})
        else:
            response = self._handle_rag_turn(session_id, message)

        self._chat_memory.add_message(session_id, "assistant", response.answer)
        return response

    def _handle_booking_turn(
        self,
        db: Session,
        session_id: str,
        message: str,
        booking_state: dict[str, str | None],
    ) -> ChatResponse:
        history = self._chat_memory.get_history(session_id)
        conversation_context = "\n".join(f"{m.role}: {m.content}" for m in history[:-1])

        extracted = self._llm_client.extract_booking_slots(conversation_context, message)
        merged_slots = BookingService.merge_slots(booking_state, extracted)

        validation_errors = BookingService.validate_slots(merged_slots)
        if validation_errors:
            self._chat_memory.set_booking_state(session_id, merged_slots)
            answer = (
                "I found an issue with the details provided: "
                + "; ".join(validation_errors)
                + ". Could you please correct and resend them?"
            )
            return ChatResponse(session_id=session_id, answer=answer, intent="booking")

        missing = BookingService.missing_fields(merged_slots)
        if missing:
            self._chat_memory.set_booking_state(session_id, merged_slots)
            answer = self._ask_for_missing_fields(missing)
            return ChatResponse(session_id=session_id, answer=answer, intent="booking")

        if BookingService.is_slot_taken(db, merged_slots["interview_date"], merged_slots["interview_time"]):
            taken_date, taken_time = merged_slots["interview_date"], merged_slots["interview_time"]
            merged_slots = {**merged_slots, "interview_date": None, "interview_time": None}
            self._chat_memory.set_booking_state(session_id, merged_slots)
            answer = (
                f"Sorry, {taken_date} at {taken_time} is already booked. "
                "Could you share a different date and/or time?"
            )
            return ChatResponse(session_id=session_id, answer=answer, intent="booking")

        booking = BookingService.create_booking(db, session_id, merged_slots)
        self._chat_memory.clear_booking_state(session_id)
        answer = (
            f"Your interview is booked for {booking.interview_date} at {booking.interview_time}. "
            f"A confirmation will be sent to {booking.email}."
        )
        return ChatResponse(session_id=session_id, answer=answer, intent="booking", booking_id=booking.id)

    def _handle_rag_turn(self, session_id: str, message: str) -> ChatResponse:
        query_vector = self._embedding_client.embed_query(message)
        retrieved = self._vector_store.search(query_vector=query_vector, top_k=settings.top_k_results)

        context = "\n\n".join(f"[{i + 1}] {chunk.text}" for i, chunk in enumerate(retrieved))
        history = self._chat_memory.get_history(session_id)

        messages = [{"role": m.role, "content": m.content} for m in history[:-1]]
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nQuestion: {message}"})

        answer = self._llm_client.generate_answer(_RAG_SYSTEM_PROMPT, messages)
        sources = [
            RetrievedSource(
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                score=chunk.score,
                text=chunk.text,
            )
            for chunk in retrieved
        ]
        return ChatResponse(session_id=session_id, answer=answer, intent="rag_query", sources=sources)

    def _ask_for_missing_fields(self, missing: list[str]) -> str:
        field_labels = {
            "name": "your full name",
            "email": "your email address",
            "interview_date": "the interview date (YYYY-MM-DD)",
            "interview_time": "the interview time (HH:MM)",
        }
        readable = ", ".join(field_labels[field] for field in missing)
        return f"Sure, I can help schedule your interview. Could you please share {readable}?"


def _mentions_booking_intent(message: str) -> bool:
    lowered = message.lower()
    return any(keyword in lowered for keyword in _BOOKING_INTENT_KEYWORDS)
