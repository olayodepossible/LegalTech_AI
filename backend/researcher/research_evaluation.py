"""
Evaluator + optional Google (Serper) search refinement for `run_research_agent`.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

import os
from pydantic import BaseModel, Field, field_validator

from agents import Agent, Runner, trace
from agents.extensions.models.litellm_model import LitellmModel

from context import get_evaluator_instructions, get_search_refiner_instructions
from tools import serper_google_search, serper_search_configured

logger = logging.getLogger(__name__)


class ResearchEvaluation(BaseModel):
    """Structured output from the review agent."""

    adequate: bool
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    issues: str = ""
    suggested_search_queries: list[str] = Field(default_factory=list)

    @field_validator("suggested_search_queries", mode="before")
    @classmethod
    def _coerce_queries(cls, v: object) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []


def _strip_json_fences(text: str) -> str:
    t = text.strip()
    if "```" in t:
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()


def _parse_eval_json(text: str) -> ResearchEvaluation:
    raw = _strip_json_fences(text)
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        raw = m.group(0)
    return ResearchEvaluation.model_validate_json(raw)


def get_research_litellm_model() -> LitellmModel:
    return LitellmModel(
        f"openrouter/openai/{os.getenv('OPENAI_CHAT_MODEL')}", api_key=os.getenv("OPENROUTER_API_KEY")
    )


def needs_search_refinement(ev: ResearchEvaluation) -> bool:
    """Heuristic: rerun with web search when the reviewer is not confident or flags inadequacy or halucinations."""
    if not ev.adequate:
        return True
    if ev.confidence < 0.65:
        return True
    return False


async def evaluate_research_output(
    user_query: str, draft_output: str, model: Optional[LitellmModel] = None
) -> ResearchEvaluation:
    """
    Second agent: no tools. Returns structured judgment on whether the draft answers the request.
    On parse failure, returns a conservative "adequate" result so the pipeline still completes.
    """
    model = model or get_research_litellm_model()
    agent = Agent(
        name="Research output evaluator",
        instructions=get_evaluator_instructions(),
        model=model,
    )
    user_input = (
        f"USER_QUERY:\n{user_query}\n\n"
        f"DRAFT_OUTPUT:\n{draft_output}\n\n"
        "Respond with the required JSON object only."
    )
    with trace("Researcher-evaluate"):
        result = await Runner.run(agent, input=user_input, max_turns=4)
    raw = (result.final_output or "").strip()
    try:
        return _parse_eval_json(raw)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("Evaluator JSON parse failed: %s — raw: %s", e, raw[:500])
        return ResearchEvaluation(
            adequate=True,
            confidence=0.5,
            issues="Evaluator could not parse model output; accepting draft.",
            suggested_search_queries=[],
        )


async def refine_research_with_serper(
    user_query: str,
    draft_output: str,
    ev: ResearchEvaluation,
    model: Optional[LitellmModel] = None,
) -> str | None:
    """
    Third agent: uses Serper (Google) via ``serper_google_search`` function tool.
    Returns improved text, or None if Serper is not configured.
    """
    if not serper_search_configured():
        logger.info("SERPER_API_KEY not set; skipping Google search refinement")
        return None

    model = model or get_research_litellm_model()
    queries = ev.suggested_search_queries or []
    q_block = "\n".join(f"- {q}" for q in queries) or "(use your own queries from the issues)"

    user_input = (
        f"USER_QUERY:\n{user_query}\n\n"
        f"DRAFT (may be incomplete):\n{draft_output}\n\n"
        f"EVALUATION ISSUES:\n{ev.issues or '(none)'}\n\n"
        f"SUGGESTED SEARCH QUERIES:\n{q_block}\n\n"
        "Use serper_google_search as needed, then output the final improved research note in markdown."
    )

    with trace("Researcher-serper-refine"):
        agent = Agent(
            name="Legal research refiner (Serper / Google search)",
            instructions=get_search_refiner_instructions(),
            model=model,
            tools=[serper_google_search],
        )
        result = await Runner.run(agent, input=user_input, max_turns=12)

    out = (result.final_output or "").strip()
    return out or None
