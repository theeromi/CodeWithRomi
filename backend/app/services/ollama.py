import asyncio
import json
import logging
from typing import AsyncIterator

import httpx

from app.config import get_settings

settings = get_settings()
log = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    pass


# Retry policy for transient connection errors. Ollama can be briefly
# unreachable while it loads a model into VRAM, restarts a service, etc.
# We retry a few times with exponential backoff so a single blip doesn't
# fail an entire ingest pipeline.
_RETRY_ATTEMPTS = 3
_RETRY_BASE_SECONDS = 2.0
_TRANSIENT_STATUSES = {502, 503, 504}


async def _post_with_retry(client: httpx.AsyncClient, url: str, json_payload: dict) -> httpx.Response:
    """POST that retries on connection errors and 5xx-class responses.
    Re-raises the last error if all attempts exhaust."""
    last_exc: Exception | None = None
    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            r = await client.post(url, json=json_payload)
            if r.status_code in _TRANSIENT_STATUSES and attempt < _RETRY_ATTEMPTS:
                log.warning("ollama %s returned %s; retrying (%d/%d)", url, r.status_code, attempt, _RETRY_ATTEMPTS)
                await asyncio.sleep(_RETRY_BASE_SECONDS * attempt)
                continue
            return r
        except (httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError, httpx.ReadTimeout) as e:
            last_exc = e
            if attempt < _RETRY_ATTEMPTS:
                log.warning("ollama %s connection error: %s; retrying (%d/%d)", url, e, attempt, _RETRY_ATTEMPTS)
                await asyncio.sleep(_RETRY_BASE_SECONDS * attempt)
                continue
            raise
    # Shouldn't reach here, but pacify the type checker
    if last_exc:
        raise last_exc
    raise OllamaError("unreachable")


def _resolved_chat_model(override: str | None) -> str:
    if override:
        return override
    # Defer the import to runtime to avoid a circular import at module load.
    from app.services.settings_store import current_chat_model
    return current_chat_model()


def _resolved_embed_model() -> str:
    from app.services.settings_store import current_embed_model
    return current_embed_model()


async def embed(text: str) -> list[float]:
    model = _resolved_embed_model()
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await _post_with_retry(
            client,
            f"{settings.ollama_base_url}/api/embeddings",
            {"model": model, "prompt": text},
        )
        if r.status_code != 200:
            raise OllamaError(f"embed failed: {r.status_code} {r.text}")
        data = r.json()
        emb = data.get("embedding")
        if not emb:
            raise OllamaError(f"embed returned no embedding: {data}")
        return emb


async def embed_batch(texts: list[str]) -> list[list[float]]:
    return [await embed(t) for t in texts]


async def chat_complete(messages: list[dict], model: str | None = None) -> str:
    """Non-streaming chat completion."""
    use_model = _resolved_chat_model(model)
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await _post_with_retry(
            client,
            f"{settings.ollama_base_url}/api/chat",
            {"model": use_model, "messages": messages, "stream": False},
        )
        if r.status_code != 200:
            raise OllamaError(f"chat failed: {r.status_code} {r.text}")
        data = r.json()
        return data.get("message", {}).get("content", "")


async def chat_stream(messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
    """Streaming chat completion. Yields content tokens as they arrive.

    No retry on stream interruption: by the time we'd retry, the user has
    already seen partial tokens and a silent restart would corrupt the UI's
    accumulated buffer. We surface the error and let the caller decide.
    """
    use_model = _resolved_chat_model(model)
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{settings.ollama_base_url}/api/chat",
            json={"model": use_model, "messages": messages, "stream": True},
        ) as r:
            if r.status_code != 200:
                body = await r.aread()
                raise OllamaError(f"chat stream failed: {r.status_code} {body.decode(errors='replace')}")
            async for line in r.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("done"):
                    return
                token = obj.get("message", {}).get("content")
                if token:
                    yield token


async def health() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


async def list_models() -> list[dict]:
    """Returns Ollama's locally-pulled models with size + modified date.

    Shape per item: {name, size, modified_at, parameter_size, family}.
    Returns [] on any failure (the UI can degrade gracefully)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{settings.ollama_base_url}/api/tags")
            if r.status_code != 200:
                return []
            payload = r.json()
            out = []
            for m in payload.get("models", []):
                details = m.get("details") or {}
                out.append({
                    "name": m.get("name"),
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at"),
                    "parameter_size": details.get("parameter_size"),
                    "family": details.get("family"),
                })
            # Sort by size desc so big models are visually prominent
            out.sort(key=lambda x: -(x["size"] or 0))
            return out
    except Exception as e:
        log.warning("list_models failed: %s", e)
        return []
