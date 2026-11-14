import re
from enum import Enum
from typing import Protocol


class ChunkingStrategy(str, Enum):
    FIXED_SIZE = "fixed_size"
    SENTENCE = "sentence"


class Chunker(Protocol):
    def chunk(self, text: str) -> list[str]: ...


class FixedSizeChunker:
    """Splits normalized text into overlapping fixed-size character windows."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        chunks: list[str] = []
        start = 0
        text_length = len(normalized)
        step = self.chunk_size - self.chunk_overlap

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            chunks.append(normalized[start:end].strip())
            if end == text_length:
                break
            start += step

        return [c for c in chunks if c]


class SentenceChunker:
    """Groups consecutive sentences together up to a maximum character budget."""

    _SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, max_chars: int = 1000, sentence_overlap: int = 1) -> None:
        self.max_chars = max_chars
        self.sentence_overlap = max(0, sentence_overlap)

    def chunk(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        sentences = [s.strip() for s in self._SENTENCE_BOUNDARY.split(normalized) if s.strip()]
        if not sentences:
            return []

        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for sentence in sentences:
            if current and current_len + len(sentence) + 1 > self.max_chars:
                chunks.append(" ".join(current))
                current = current[-self.sentence_overlap :] if self.sentence_overlap else []
                current_len = sum(len(s) + 1 for s in current)

            current.append(sentence)
            current_len += len(sentence) + 1

        if current:
            chunks.append(" ".join(current))

        return chunks


def get_chunker(strategy: ChunkingStrategy) -> Chunker:
    if strategy is ChunkingStrategy.FIXED_SIZE:
        return FixedSizeChunker()
    if strategy is ChunkingStrategy.SENTENCE:
        return SentenceChunker()
    raise ValueError(f"Unknown chunking strategy: {strategy}")
