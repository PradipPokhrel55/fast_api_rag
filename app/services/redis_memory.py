import json
from datetime import datetime, timezone

import redis

from app.config import get_settings
from app.schemas.chat import ChatMessageSchema

settings = get_settings()

_HISTORY_KEY_PREFIX = "chat:history:"
_BOOKING_KEY_PREFIX = "chat:booking:"


class ChatMemory:
    """Redis-backed conversation memory: message history plus in-progress booking slots."""

    def __init__(self, client: redis.Redis | None = None) -> None:
        self._client = client or redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        key = f"{_HISTORY_KEY_PREFIX}{session_id}"
        message = {"role": role, "content": content, "timestamp": datetime.now(timezone.utc).isoformat()}
        self._client.rpush(key, json.dumps(message))
        self._client.expire(key, settings.chat_history_ttl_seconds)

    def get_history(self, session_id: str, max_turns: int | None = None) -> list[ChatMessageSchema]:
        key = f"{_HISTORY_KEY_PREFIX}{session_id}"
        limit = max_turns if max_turns is not None else settings.chat_history_max_turns
        raw_messages = self._client.lrange(key, -limit * 2, -1)
        return [ChatMessageSchema(**json.loads(raw)) for raw in raw_messages]

    def get_booking_state(self, session_id: str) -> dict[str, str | None] | None:
        """Returns None if no booking is in progress, distinct from an in-progress booking with no slots filled yet."""
        key = f"{_BOOKING_KEY_PREFIX}{session_id}"
        raw = self._client.get(key)
        return json.loads(raw) if raw is not None else None

    def set_booking_state(self, session_id: str, state: dict[str, str | None]) -> None:
        key = f"{_BOOKING_KEY_PREFIX}{session_id}"
        self._client.set(key, json.dumps(state), ex=settings.chat_history_ttl_seconds)

    def clear_booking_state(self, session_id: str) -> None:
        self._client.delete(f"{_BOOKING_KEY_PREFIX}{session_id}")
