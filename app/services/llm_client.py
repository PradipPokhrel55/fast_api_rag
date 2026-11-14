import json
from typing import Any

from openai import OpenAI

from app.config import get_settings
from app.schemas.booking import BookingSlots

settings = get_settings()

_BOOKING_TOOL = {
    "type": "function",
    "function": {
        "name": "extract_interview_booking_details",
        "description": (
            "Extract any interview booking details (name, email, date, time) mentioned "
            "in the user's latest message. Omit fields that were not mentioned."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"], "description": "Candidate's full name"},
                "email": {"type": ["string", "null"], "description": "Candidate's email address"},
                "interview_date": {
                    "type": ["string", "null"],
                    "description": "Requested interview date in YYYY-MM-DD format",
                },
                "interview_time": {
                    "type": ["string", "null"],
                    "description": "Requested interview time in 24h HH:MM format",
                },
            },
            "required": [],
        },
    },
}


class LlmClient:
    """Chat completions via Groq's OpenAI-compatible API."""

    def __init__(self, client: OpenAI | None = None, model: str | None = None) -> None:
        self._client = client or OpenAI(api_key=settings.groq_api_key, base_url=settings.groq_base_url)
        self._model = model or settings.groq_chat_model

    def generate_answer(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system_prompt}, *messages],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def extract_booking_slots(self, conversation_context: str, latest_message: str) -> BookingSlots:
        system_prompt = (
            "You help schedule candidate interviews. Read the conversation and extract any "
            "booking details present only in the latest user message."
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Conversation so far:\n{conversation_context}\n\nLatest message:\n{latest_message}",
            },
        ]

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=[_BOOKING_TOOL],
            tool_choice={"type": "function", "function": {"name": "extract_interview_booking_details"}},
            temperature=0,
        )

        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            return BookingSlots()

        arguments = json.loads(tool_calls[0].function.arguments or "{}")
        return BookingSlots(**arguments)
