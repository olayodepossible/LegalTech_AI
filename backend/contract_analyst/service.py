"""OpenAI-powered contract analysis with structured Pydantic output."""

from __future__ import annotations

import logging
import os

from openai import AsyncOpenAI

from contract_analyst.schemas import ContractAnalysisResult
from contract_analyst.text_extract import extract_text_from_bytes

logger = logging.getLogger(__name__)

_MAX_CHARS = 120_000


def _truncate(text: str) -> str:
    if len(text) <= _MAX_CHARS:
        return text
    return text[:_MAX_CHARS] + "\n\n[... truncated for model context ...]"


async def analyze_contract_bytes(
    *,
    data: bytes,
    filename: str,
    user_message: str | None,
    language: str | None,
) -> ContractAnalysisResult:
    raw = extract_text_from_bytes(data, filename)
    if not raw.strip():
        raise ValueError(
            "No readable text found in the file. Try a text-based PDF or a .txt file."
        )
    text = _truncate(raw)
    return await analyze_contract_text(
        contract_text=text,
        user_message=user_message,
        language=language,
        source_filename=filename,
    )


async def analyze_contract_text(
    *,
    contract_text: str,
    user_message: str | None,
    language: str | None,
    source_filename: str | None = None,
) -> ContractAnalysisResult:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    model = os.getenv("OPENAI_CONTRACT_MODEL", "gpt-4o-mini")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url )

    lang_hint = (
        f"Respond in {language} where natural for summaries and labels."
        if language
        else "Use clear professional English."
    )
    user_extra = (user_message or "").strip()
    fname = source_filename or "document"

    system = (
        "You are an experienced contracts lawyer assistant. "
        "Analyze the contract text and produce structured findings. "
        "Be precise; if the text is not a contract, say so in the executive_summary and keep lists minimal. "
        "Do not invent clauses not supported by the text. "
        + lang_hint
    )
    user_prompt = (
        f"File name: {fname}\n\n"
        f"Contract text:\n---\n{contract_text}\n---\n"
    )
    if user_extra:
        user_prompt += f"\nUser focus / question:\n{user_extra}\n"

    try:
        completion = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            response_format=ContractAnalysisResult,
        )
    except Exception as e:
        logger.exception("OpenAI contract parse failed: %s", e)
        raise RuntimeError(
            "Contract analysis failed. Check logs and API configuration."
        ) from e

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("Model returned no structured output")
    return parsed
