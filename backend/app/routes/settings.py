"""Read and update runtime-mutable settings (currently: chat model)."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.auth import get_current_user
from app.models import User
from app.services import ollama, settings_store

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ModelInfo(BaseModel):
    name: str
    size: int
    parameter_size: str | None = None
    family: str | None = None
    modified_at: str | None = None


class SettingsResponse(BaseModel):
    chat_model: str
    embed_model: str
    available_models: list[ModelInfo]
    ollama_reachable: bool


class UpdateChatModelRequest(BaseModel):
    chat_model: str = Field(min_length=1, max_length=128)


@router.get("", response_model=SettingsResponse)
async def get_settings_view(_: User = Depends(get_current_user)) -> SettingsResponse:
    available = await ollama.list_models()
    reachable = await ollama.health()
    return SettingsResponse(
        chat_model=settings_store.current_chat_model(),
        embed_model=settings_store.current_embed_model(),
        available_models=[ModelInfo(**m) for m in available],
        ollama_reachable=reachable,
    )


@router.put("/chat-model", response_model=SettingsResponse)
async def update_chat_model(
    payload: UpdateChatModelRequest,
    _: User = Depends(get_current_user),
) -> SettingsResponse:
    available = await ollama.list_models()
    available_names = {m["name"] for m in available}
    # Ollama treats `<name>` as an alias for `<name>:latest`. Accept either form.
    requested = payload.chat_model
    resolved = (
        requested if requested in available_names
        else f"{requested}:latest" if f"{requested}:latest" in available_names
        else None
    )
    if not resolved:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Model '{requested}' is not pulled on the host. Run `ollama pull {requested}` first.",
        )
    settings_store.set_chat_model(resolved)
    reachable = await ollama.health()
    return SettingsResponse(
        chat_model=settings_store.current_chat_model(),
        embed_model=settings_store.current_embed_model(),
        available_models=[ModelInfo(**m) for m in available],
        ollama_reachable=reachable,
    )
