# FastAPI RAG Backend

Modular FastAPI backend exposing two REST APIs:

1. **Document Ingestion API** — upload `.pdf`/`.txt` files, chunk with a selectable strategy,
   embed locally (free, no API key), and store vectors in **Qdrant** with metadata in a **SQL** database.
2. **Conversational RAG API** — custom retrieval + generation pipeline (no `RetrievalQAChain`),
   multi-turn memory in **Redis**, and LLM-driven interview booking slot extraction via **Groq**.

## Architecture

```
app/
  main.py                FastAPI app, lifespan startup (DB init)
  config.py               Settings (pydantic-settings, .env driven)
  core/                    Cross-cutting concerns (logging, exceptions)
  db/                      SQLAlchemy models, session/engine, Base
  schemas/                 Pydantic request/response models
  services/
    text_extraction.py     PDF/TXT -> raw text
    chunking.py             FixedSizeChunker + SentenceChunker (Strategy pattern)
    embeddings.py            Local fastembed (ONNX) embeddings wrapper, no API key
    vector_store.py          Qdrant client wrapper (upsert/search), supports API key auth
    llm_client.py             Groq (OpenAI-compatible) chat completions + tool-calling slot extraction
    redis_memory.py           Chat history + booking-slot state in Redis
    booking_service.py        Slot merge/validation/persistence
    ingestion_service.py      Orchestrates extraction -> chunk -> embed -> store
    rag_service.py            Orchestrates a chat turn (RAG vs booking flow)
  api/
    deps.py                   Cached service providers (DI)
    v1/endpoints/              ingestion.py, chat.py, bookings.py
```

## Why these choices

- **Vector store:** Qdrant (self-hostable, Cloud, or embedded in-process via
  `QDRANT_LOCAL_PATH` — no server/Docker needed at all; excludes FAISS/Chroma per constraints).
  Set `QDRANT_API_KEY` for Qdrant Cloud, or leave it empty for an unauthenticated local instance.
- **LLM:** Groq's free tier, accessed through its OpenAI-compatible endpoint
  (`GROQ_BASE_URL=https://api.groq.com/openai/v1`), using `openai/gpt-oss-20b` by default
  (supports tool/function calling, needed for booking-slot extraction).
- **Embeddings:** Groq has no embeddings endpoint, so `EmbeddingClient` runs `fastembed`
  (`BAAI/bge-small-en-v1.5`, 384-dim) fully locally — no API key, no cost.
- **Chunking strategies:** `fixed_size` (overlapping character windows) and `sentence`
  (groups whole sentences up to a character budget), selectable via query param.
- **Custom RAG:** retrieval (Qdrant search) and generation (Groq chat completion) are
  wired manually in `RagService` — no LangChain `RetrievalQAChain`.
- **Chat memory:** Redis list per `session_id`, TTL-bound, capped to last N turns. No auth
  required for a default local Redis — just set `REDIS_URL` (include credentials in the URL
  if your instance needs them, e.g. `redis://:password@host:6379/0`).
- **Interview booking:** Groq tool-calling extracts `name/email/date/time` from each
  message; partial slots persist in Redis until complete, then a row is written to SQL.

## Setup

### Option A — Docker (Qdrant + Redis as containers)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY (and QDRANT_API_KEY if using Qdrant Cloud)
docker compose up -d   # starts Qdrant + Redis
uvicorn app.main:app --reload
```

### Option B — Python only, no Docker

1. **Redis** — install natively and run it as a local process (no container):
   ```bash
   brew install redis      # macOS; use your OS package manager otherwise
   redis-server --daemonize yes
   ```
   `REDIS_URL=redis://localhost:6379/0` in `.env` then just works.

2. **Qdrant** — pick one, no server process required for either:
   - **Embedded (fully offline, simplest):** in `.env` set
     `QDRANT_LOCAL_PATH=./qdrant_storage` and leave `QDRANT_URL`/`QDRANT_API_KEY` as-is —
     `QDRANT_LOCAL_PATH` takes precedence and runs Qdrant in-process, persisted to that folder.
   - **Qdrant Cloud:** leave `QDRANT_LOCAL_PATH` empty, set `QDRANT_URL` to your cluster's
     endpoint (from the Qdrant Cloud dashboard) and `QDRANT_API_KEY` to its key.

3. **Everything else** (SQLite, Groq, fastembed) needs no server at all.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY; set QDRANT_LOCAL_PATH=./qdrant_storage
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for interactive API docs.

## Endpoints

### Document Ingestion

- `POST /api/v1/documents/upload?chunking_strategy=fixed_size|sentence` (multipart file)
- `GET /api/v1/documents`
- `GET /api/v1/documents/{document_id}`

### Conversational RAG

- `POST /api/v1/chat` — `{"session_id": "optional", "message": "..."}`
- `GET /api/v1/chat/{session_id}/history`
- `GET /api/v1/bookings`, `GET /api/v1/bookings/{booking_id}`

## Example flow

```bash
curl -F "file=@notes.pdf" "http://localhost:8000/api/v1/documents/upload?chunking_strategy=sentence"

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What does the document say about onboarding?"}'

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<id>", "message": "Book an interview for John Doe, john@example.com, on 2026-12-01 at 14:00"}'
```

## Notes

- Default SQL store is SQLite (`DATABASE_URL`); swap in Postgres by changing the URL.
- Swap embedding/LLM providers by implementing the same method signatures as
  `EmbeddingClient`/`LlmClient` and updating `app/api/deps.py`.
- Groq free-tier rate limits are modest; if you hit `429`s, switch `GROQ_CHAT_MODEL` to a
  lighter model such as `openai/gpt-oss-20b`, or check `GET https://api.groq.com/openai/v1/models`
  (with your key) for the exact model ids your account has access to — availability varies.
- The first `fastembed` call downloads the ONNX model (~130MB) to a local cache; subsequent
  runs are fully offline.
