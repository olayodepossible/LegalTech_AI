"""LLM provider abstraction. Production: OpenAI, Llama via vLLM, etc."""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


class LLMClient(Protocol):
    async def complete(self, system: str, user: str, *, language: str | None = None) -> str: ...


class StubLLMClient:
    """Returns placeholder analysis when no remote LLM is configured."""

    async def complete(self, system: str, user: str, *, language: str | None = None) -> str:
        lang = f" [{language}]" if language else ""
        logger.info("llm.stub.complete lang=%s user_chars=%s", language, len(user))
        return (
            f"[stub LLM{lang}] Analyze the following in production with your configured provider.\n\n"
            f"--- System ---\n{system[:500]}{'…' if len(system) > 500 else ''}\n\n"
            f"--- User ---\n{user[:1500]}{'…' if len(user) > 1500 else ''}"
        )


class HttpLLMClient:
    """Generic OpenAI-compatible chat completions endpoint."""

    def __init__(self, base_url: str | None, api_key: str | None) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key

    async def complete(self, system: str, user: str, *, language: str | None = None) -> str:
        if not self.base_url:
            return await StubLLMClient().complete(system, user, language=language)
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user + (f"\n\nRespond in {language}." if language else "")},
            ],
        }
        url = f"{self.base_url}/v1/chat/completions"
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]


def build_llm_client(base_url: str | None, api_key: str | None) -> LLMClient:
    if base_url:
        return HttpLLMClient(base_url, api_key)
    return StubLLMClient()
