import json
from typing import AsyncIterator

import httpx

from app.config import get_settings

settings = get_settings()


class OllamaError(RuntimeError):
    pass


async def embed(text: str) -> list[float]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
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
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model or settings.ollama_chat_model,
                "messages": messages,
                "stream": False,
            },
        )
        if r.status_code != 200:
            raise OllamaError(f"chat failed: {r.status_code} {r.text}")
        data = r.json()
        return data.get("message", {}).get("content", "")


async def chat_stream(messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
    """Streaming chat completion. Yields content tokens as they arrive."""
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": model or settings.ollama_chat_model,
                "messages": messages,
                "stream": True,
            },
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
