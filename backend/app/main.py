import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.db import engine
from app.routes import auth, chat, documents, search
from app.services import ollama

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
)
log = logging.getLogger("vaultai")

settings = get_settings()
app = FastAPI(title="VaultAI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(search.router)
app.include_router(chat.router)


@app.on_event("startup")
def on_startup() -> None:
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    db_path = settings.database_url.replace("sqlite:///", "")
    if db_path and not db_path.startswith(":"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    from app.db import Base
    import app.models  # noqa: F401  ensure models registered

    Base.metadata.create_all(bind=engine)
    _ensure_extras()
    log.info("DB ready at %s", settings.database_url)
    log.info("Ollama endpoint: %s", settings.ollama_base_url)


def _ensure_extras() -> None:
    """Create sqlite-vec virtual table + FTS5 mirror + triggers (idempotent).
    Also retrofits any nullable columns added after the initial schema."""
    with engine.begin() as conn:
        # Retrofit chats.document_id (added for document-scoped chats). SQLite
        # doesn't support IF NOT EXISTS on ADD COLUMN, so we probe pragma first.
        cols = {row[1] for row in conn.execute(text("PRAGMA table_info(chats)")).all()}
        if "document_id" not in cols:
            conn.execute(text("ALTER TABLE chats ADD COLUMN document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_chats_document_id ON chats(document_id)"))

        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_vec USING vec0("
            "chunk_id INTEGER PRIMARY KEY, embedding float[768])"
        ))
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts "
            "USING fts5(text, content='chunks', content_rowid='id', tokenize='porter unicode61')"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN "
            "INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text); END"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN "
            "INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text); END"
        ))
        conn.execute(text(
            "CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN "
            "INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.id, old.text); "
            "INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text); END"
        ))


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "ollama": await ollama.health(),
        "chat_model": settings.ollama_chat_model,
        "embed_model": settings.ollama_embed_model,
    }
