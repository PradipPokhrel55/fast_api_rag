from fastembed import TextEmbedding

from app.config import get_settings

settings = get_settings()


class EmbeddingClient:
    """Local, API-key-free embeddings (ONNX via fastembed) — Groq has no embeddings endpoint."""

    def __init__(self, model: TextEmbedding | None = None, model_name: str | None = None) -> None:
        self._model = model or TextEmbedding(model_name=model_name or settings.embedding_model_name)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [embedding.tolist() for embedding in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]
