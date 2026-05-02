"""Runtime-mutable configuration backed by the app_settings KV table.

Each setting falls back to its env default when no DB override exists, so
the very first boot still works the same way. The UI writes overrides here,
and the rest of the app reads through `current_*` accessors so the value is
always live (no container restart required).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import AppSetting

KEY_CHAT_MODEL = "chat_model"
KEY_EMBED_MODEL = "embed_model"


def _get(db: Session, key: str) -> str | None:
    return db.execute(select(AppSetting.value).where(AppSetting.key == key)).scalar()


def _set(db: Session, key: str, value: str) -> None:
    existing = db.get(AppSetting, key)
    if existing:
        existing.value = value
    else:
        db.add(AppSetting(key=key, value=value))
    db.commit()


def current_chat_model() -> str:
    """Resolve the active chat model: DB override → env default."""
    db = SessionLocal()
    try:
        return _get(db, KEY_CHAT_MODEL) or get_settings().ollama_chat_model
    finally:
        db.close()


def current_embed_model() -> str:
    """Resolve the active embedding model: DB override → env default.

    Note: changing the embed model invalidates every stored vector. The UI
    keeps this read-only for now; we only expose a setter for symmetry.
    """
    db = SessionLocal()
    try:
        return _get(db, KEY_EMBED_MODEL) or get_settings().ollama_embed_model
    finally:
        db.close()


def set_chat_model(model: str) -> None:
    db = SessionLocal()
    try:
        _set(db, KEY_CHAT_MODEL, model)
    finally:
        db.close()
