# VaultAI

A privacy-first, self-hosted "Private ChatGPT for your files." Upload PDFs, DOCX, or text, get AI-generated summaries, search across everything, and chat with your documents — all powered by a local Ollama model. **No external AI APIs.**

- **Frontend:** React + TypeScript + Vite + Tailwind + shadcn-style UI
- **Backend:** Python + FastAPI + SQLAlchemy
- **Storage:** SQLite (with `sqlite-vec` for embeddings + FTS5 for keyword search)
- **AI:** Ollama running on the host (so it can use your GPU / eGPU)

---

## Prerequisites

1. **Docker Desktop** (or Docker + docker-compose).
2. **Ollama** installed natively on the host (`https://ollama.com/download`). Running Ollama on the host — not in a container — is the reliable way to use a Windows eGPU.
3. Pull the models you want to use:

   ```bash
   ollama pull llama3.2:3b           # default chat model (small, fast)
   ollama pull nomic-embed-text      # default embedding model
   # Optional: a larger chat model if your eGPU has the VRAM
   ollama pull qwen2.5:7b
   ```

4. Make sure Ollama is reachable on `http://localhost:11434` (run `ollama serve` if it's not already a service).

---

## Run it

```bash
cp .env.example .env          # edit JWT_SECRET at minimum
docker compose up --build
```

Then open **http://localhost:8090** and register your account.

The backend API is on `http://localhost:8000` (Swagger UI at `/docs`).

To switch chat model without rebuilding:

```bash
OLLAMA_CHAT_MODEL=qwen2.5:7b docker compose up
```

---

## Architecture

```
React SPA  ──►  FastAPI  ──►  Ollama (host, GPU)
                   │
                   ├──►  SQLite (metadata + FTS5)
                   ├──►  sqlite-vec (embeddings, same DB file)
                   └──►  ./data/uploads/  (raw files)
```

Backend reaches Ollama at `http://host.docker.internal:11434` from inside the container.

### Document pipeline

```
Upload → extract (pypdf / python-docx / plain text)
       → chunk (~800 tokens, 100 overlap)
       → embed (Ollama nomic-embed-text)  → sqlite-vec
       → summarize (Ollama chat model)    → documents.summary
       → ready
```

Status is polled by the UI so you can watch progress on big files.

### RAG chat

```
Question → embed → sqlite-vec KNN (top 5)
        → build prompt (system + excerpts + history + question)
        → Ollama streaming chat → SSE → UI renders tokens + citations
```

---

## Project structure

```
vaultai/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── app/
│       ├── main.py            # FastAPI app, FTS5/vec setup, /api/health
│       ├── config.py          # env-driven settings
│       ├── db.py              # SQLAlchemy + sqlite-vec loader
│       ├── models.py
│       ├── schemas.py
│       ├── auth.py            # JWT — single dependency, swap for Ghost SSO later
│       ├── routes/            # auth · documents · search · chat
│       └── services/          # extraction · chunking · ollama · pipeline · retrieval
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── src/
        ├── App.tsx
        ├── lib/api.ts         # fetch wrapper + JWT
        ├── hooks/             # useAuth · useTheme · useToast
        ├── components/        # Layout · DocumentCard · StatusBadge · ui/*
        └── routes/            # Login · Dashboard · Upload · DocumentView · Chat
```

`./data/` holds the SQLite DB (`app.db`) and `uploads/`. It's bind-mounted into the backend container and gitignored.

---

## Configuration

All settings come from `.env` / docker-compose env. The most important ones:

| Variable             | Default              | Notes |
|----------------------|----------------------|-------|
| `JWT_SECRET`         | `dev-secret-change-me` | **Change this** before exposing the app. |
| `ALLOW_REGISTRATION` | `true`               | Set to `false` after creating your account. |
| `OLLAMA_CHAT_MODEL`  | `llama3.2:3b`        | Any model you've pulled. |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text`   | Embedding dimension is fixed at 768 in `main.py` — change there if you swap to a different-dimension model. |
| `CORS_ORIGINS`       | `http://localhost:5173,http://localhost:8090` | Comma-separated. |

---

## Local development (without Docker)

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .
DATABASE_URL=sqlite:///./data/app.db UPLOAD_DIR=./data/uploads \
  uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173 — proxies /api to http://localhost:8000
```

---

## Roadmap (deferred from MVP)

- **Ghost Members SSO** — replace `app/auth.py:get_current_user` with a Ghost JWT validator so codewithromi.com members can log in directly.
- **n8n integration** — webhooks for `/ingest` (auto-add docs from a folder/email) and `/query` (Slack-style assistant).
- **OCR** — `pytesseract` is wired into the extraction code; flip a flag to enable image extraction.
- **Job queue** — swap `BackgroundTasks` for RQ or Celery before going multi-user (so a worker restart doesn't strand a doc).
- **Folder auto-watch**, **smart tagging**, **multi-user quotas**, **GPU profiles**, **Tailscale remote access**.

---

## Troubleshooting

- **`/api/health` returns `ollama: false`** — the backend can't reach `http://host.docker.internal:11434`. On Linux, `extra_hosts: host.docker.internal:host-gateway` (already set in compose) is required. On Mac/Windows it works out of the box. Make sure `ollama serve` is running.
- **`embedding dimensions mismatch`** — you swapped embed model to one with a different dimension. Edit `backend/app/main.py` (`embedding float[768]`) and delete the existing `chunk_vec` table.
- **PDF extracts as empty text** — likely a scanned PDF. Real fix is OCR (deferred); workaround is to pre-OCR the PDF before upload.
- **Chat says "I don't know"** — embeddings might still be processing. Check the dashboard status badges; the doc must be **Ready** to be retrievable.
