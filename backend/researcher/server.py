"""
Legal Researcher Service - Legal Advice Agent
"""

import logging
import os
import time
from datetime import datetime, UTC
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load repo-root `.env` before any import that reads ``SERPER_API_KEY`` (see ``tools.py``).
_repo_root = Path(__file__).resolve().parents[2]
load_dotenv(_repo_root / ".env", override=True)
load_dotenv(override=True)

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from agents import Agent, Runner, trace

# Suppress LiteLLM warnings about optional dependencies
logger = logging.getLogger(__name__)
logging.getLogger("LiteLLM").setLevel(logging.CRITICAL)
logging.getLogger("legaltech.flow").setLevel(logging.INFO)

from flow_log import log_flow, new_trace_id, trace_context

# Import from our modules
from context import (
    build_default_research_query,
    build_research_user_query,
    build_research_user_query_with_history,
    companion_message_for_code,
    get_agent_instructions,
    research_footer_optional_serper_unavailable,
    research_footer_serper,
    should_give_companion_guidance,
)
from mcp_servers import create_playwright_mcp_server
from research_evaluation import (
    evaluate_research_output,
    get_research_litellm_model,
    needs_search_refinement,
    refine_research_with_serper,
)
from tools import ingest_legal_document, serper_search_configured

app = FastAPI(title="Legal Companion Researcher Service")


class ConversationTurn(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def role_ok(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("role must be user or assistant")
        return v


# Request model # Optional - if not provided, agent picks a topic
class ResearchRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=12000)
    language: str | None = "en"
    conversation_history: list[ConversationTurn] | None = Field(
        None,
        description="Earlier turns in the same thread (optional; improves follow-up answers).",
    )

class ResearchResponse(BaseModel):
    reply: str

async def _run_primary_research_agent(user_query: str) -> str:
    """First pass: Playwright MCP + optional ingest to legal API."""
    t0 = time.perf_counter()
    log_flow(
        "research.phase.start",
        step="agent.primary",
        target="openrouter_playwright",
    )
    model = get_research_litellm_model()
    with trace("Researcher-primary"):
        async with create_playwright_mcp_server(timeout_seconds=60) as playwright_mcp:
            agent = Agent(
                name="Legal Companion Researcher",
                instructions=get_agent_instructions(),
                model=model,
                tools=[ingest_legal_document],
                mcp_servers=[playwright_mcp],
            )
            result = await Runner.run(agent, input=user_query, max_turns=15)
    out = (result.final_output or "").strip()
    log_flow(
        "research.phase.end",
        step="agent.primary",
        target="openrouter_playwright",
        duration_ms=(time.perf_counter() - t0) * 1000,
        draft_chars=len(out),
    )
    return out


async def run_research_agent(
    user_message: str | None = None,
    response_language: str = "en",
    conversation_history: list[dict] | None = None,
) -> str:
    """Run research: primary browse pass → evaluator → optional Serper (Google) refinement.

    1) Primary agent: Playwright-based browsing + ingest (existing behavior).
    2) Evaluator agent: returns JSON (adequate / confidence / issues / suggested queries).
    3) If refinement is needed and ``SERPER_API_KEY`` is set, a third agent uses the
       ``serper_google_search`` tool (Serper.dev) and produces an improved answer.
    If that optional step is skipped or does not return text, the primary draft is returned
    with a short footer (quality review already ran; only the Serper add-on may be missing).

    ``response_language`` is the BCP-47 code from the chat UI; it is woven into the agent input
    so the model must answer in that language (including for ``en``).
    """
    lang = (response_language or "en").strip() or "en"

    if user_message and should_give_companion_guidance(user_message):
        return companion_message_for_code(lang)

    if user_message:
        if conversation_history:
            query = build_research_user_query_with_history(
                user_message, lang, conversation_history
            )
        else:
            query = build_research_user_query(user_message, lang)
    else:
        query = build_default_research_query(lang)

    model = get_research_litellm_model()
    draft = await _run_primary_research_agent(query)
    if not draft:
        log_flow(
            "research.phase.skip",
            step="agent.primary",
            target="openrouter_playwright",
            reason="empty_draft",
        )
        return "No output was generated by the research agent."

    t_ev = time.perf_counter()
    log_flow("research.phase.start", step="evaluator", target="openrouter")
    ev = await evaluate_research_output(query, draft, model)
    log_flow(
        "research.phase.end",
        step="evaluator",
        target="openrouter",
        duration_ms=(time.perf_counter() - t_ev) * 1000,
        adequate=ev.adequate,
        confidence=ev.confidence,
        needs_refinement=needs_search_refinement(ev),
    )

    if not needs_search_refinement(ev):
        return draft

    try:
        log_flow(
            "research.phase.start",
            step="serper_refiner",
            target="serper_openrouter",
            serper_configured=serper_search_configured(),
        )
        t_ref = time.perf_counter()
        refined = await refine_research_with_serper(query, draft, ev, model)
        log_flow(
            "research.phase.end",
            step="serper_refiner",
            target="serper_openrouter",
            duration_ms=(time.perf_counter() - t_ref) * 1000,
            refined_chars=len(refined or ""),
        )
    except Exception as e:
        logger.exception("Serper search refinement failed: %s", e)
        log_flow(
            "research.phase.error",
            step="serper_refiner",
            target="serper_openrouter",
            exc=e,
            level=logging.ERROR,
        )
        refined = None

    if refined:
        return f"{refined}{research_footer_serper(lang)}"

    return f"{draft}{research_footer_optional_serper_unavailable(lang, serper_configured=serper_search_configured())}"

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Legal Companion Researcher",
        "status": "healthy",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/research")
async def research(request: Request, body: ResearchRequest) -> ResearchResponse:
    """
    Generate legal research and advice.

    The agent will:
    1. Browse legal websites/blogs for data
    2. Analyze the information found
    3. Store the analysis in the knowledge base

    If no topic is provided, the agent will pick a trending topic.
    """
    hdr = (request.headers.get("x-request-id") or request.headers.get("X-Request-Id") or "").strip()
    trace_id = hdr or new_trace_id()
    t0 = time.perf_counter()
    with trace_context(trace_id, "researcher"):
        log_flow(
            "request.start",
            step="post.research",
            path="/research",
            message_chars=len(body.message or ""),
            history_turns=len(body.conversation_history or []),
        )
        try:
            hist = None
            if body.conversation_history:
                hist = [t.model_dump() for t in body.conversation_history]
            response = await run_research_agent(
                body.message,
                body.language,
                conversation_history=hist,
            )
            log_flow(
                "request.end",
                step="post.research",
                path="/research",
                duration_ms=(time.perf_counter() - t0) * 1000,
                reply_chars=len(response or ""),
            )
            return ResearchResponse(reply=response)
        except Exception as e:
            log_flow(
                "request.error",
                step="post.research",
                path="/research",
                duration_ms=(time.perf_counter() - t0) * 1000,
                exc=e,
                level=logging.ERROR,
            )
            logger.exception("Error in research endpoint: %s", e)
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Detailed health check."""
    # Debug container detection
    container_indicators = {
        "dockerenv": os.path.exists("/.dockerenv"),
        "containerenv": os.path.exists("/run/.containerenv"),
        "aws_execution_env": os.environ.get("AWS_EXECUTION_ENV", ""),
        "ecs_container_metadata": os.environ.get("ECS_CONTAINER_METADATA_URI", ""),
    }

    return {
        "service": "Legal Companion Researcher",
        "status": "healthy",
        "legal_api_configured": bool(os.getenv("LEGAL_API_ENDPOINT") and os.getenv("LEGAL_API_KEY")),
        "serper_api_configured": bool(os.getenv("SERPER_API_KEY")),
        "timestamp": datetime.now(UTC).isoformat(),
        "debug_container": container_indicators,
        "aws_region": os.environ.get("AWS_DEFAULT_REGION", "not set"),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
