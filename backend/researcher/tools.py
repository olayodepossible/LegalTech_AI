"""
Tools for the Legal Companion Researcher agent
"""
import logging
import os
import time
from typing import Dict, Any
from datetime import datetime, UTC
import httpx
from agents import function_tool
from tenacity import retry, stop_after_attempt, wait_exponential

from flow_log import log_flow

# Configuration from environment (read at import time for legal API; Serper is read lazily so
# ``load_dotenv`` in ``server.py`` always runs first for local dev).
LEGAL_API_ENDPOINT = os.getenv("LEGAL_API_ENDPOINT")
LEGAL_API_KEY = os.getenv("LEGAL_API_KEY")


def _serper_api_key() -> str:
    return (os.getenv("SERPER_API_KEY") or "").strip()


def _serper_search_url() -> str:
    return (os.getenv("SERPER_SEARCH_URL") or "https://google.serper.dev/search").strip()


def serper_search_configured() -> bool:
    return bool(_serper_api_key())


def _ingest(document: Dict[str, Any]) -> Dict[str, Any]:
    """Internal function to make the actual API call."""
    ep = (LEGAL_API_ENDPOINT or "").strip()
    t0 = time.perf_counter()
    log_flow(
        "downstream.start",
        step="http.post",
        target="legal_api_ingest",
        url_host=ep.split("/")[2] if ep.startswith("http") and "/" in ep[8:] else ep[:80],
    )
    try:
        with httpx.Client() as client:
            response = client.post(
                LEGAL_API_ENDPOINT,
                json=document,
                headers={"x-api-key": LEGAL_API_KEY},
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        log_flow(
            "downstream.error",
            step="http.post",
            target="legal_api_ingest",
            duration_ms=(time.perf_counter() - t0) * 1000,
            exc=exc,
            level=logging.ERROR,
        )
        raise
    log_flow(
        "downstream.end",
        step="http.post",
        target="legal_api_ingest",
        duration_ms=(time.perf_counter() - t0) * 1000,
        http_status=200,
    )
    return data


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10)
)
def ingest_with_retries(document: Dict[str, Any]) -> Dict[str, Any]:
    """Ingest with retry logic for SageMaker cold starts."""
    return _ingest(document)


@function_tool
def serper_google_search(query: str, num_results: int = 8) -> str:
    """
    Google search via Serper (serper.dev). Returns titles, links, and snippets for organic results.

    Use 1–3 focused queries; prefer shorter queries and call again if you need a different angle.
    """
    key = _serper_api_key()
    if not key:
        return (
            "Error: Serper is not configured (set SERPER_API_KEY in the environment for Google search)."
        )
    n = max(1, min(int(num_results), 15))
    t0 = time.perf_counter()
    log_flow(
        "downstream.start",
        step="http.post",
        target="serper",
        query_chars=len(query),
        num_results=n,
    )
    try:
        with httpx.Client() as client:
            res = client.post(
                _serper_search_url(),
                json={"q": query, "num": n},
                headers={
                    "X-API-KEY": key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            text = res.text
            if not res.is_success:
                log_flow(
                    "downstream.error",
                    step="http.post",
                    target="serper",
                    duration_ms=(time.perf_counter() - t0) * 1000,
                    http_status=res.status_code,
                )
                return f"Serper API error (HTTP {res.status_code}): {text[:2000]}"
            data = res.json()
    except Exception as e:
        log_flow(
            "downstream.error",
            step="http.post",
            target="serper",
            duration_ms=(time.perf_counter() - t0) * 1000,
            exc=e,
            level=logging.WARNING,
        )
        return f"Serper request failed: {e}"
    log_flow(
        "downstream.end",
        step="http.post",
        target="serper",
        duration_ms=(time.perf_counter() - t0) * 1000,
        http_status=res.status_code,
    )

    lines: list[str] = []
    organic = data.get("organic")
    if isinstance(organic, list) and organic:
        lines.append(f"Google search results for: {query!r}\n")
        for i, item in enumerate(organic[:n], 1):
            if not isinstance(item, dict):
                continue
            title = item.get("title") or ""
            link = item.get("link") or ""
            snip = item.get("snippet") or ""
            lines.append(f"{i}. {title}\n   URL: {link}\n   {snip}\n")
    else:
        lines.append(
            f"No organic results in Serper response for {query!r}. Raw keys: {list(data.keys()) if isinstance(data, dict) else 'n/a'}"
        )

    if isinstance(data, dict) and data.get("answerBox"):
        ab = data["answerBox"]
        if isinstance(ab, dict):
            lines.insert(0, f"Answer box: {ab}\n")
    return "\n".join(lines) if lines else "Empty Serper response."


@function_tool
def ingest_legal_document(topic: str, analysis: str) -> Dict[str, Any]:
    """
    Ingest a legal document into the legal knowledge base.
    
    Args:
        topic: The topic or subject of the analysis (e.g., "AAPL Stock Analysis", "Retirement Planning Guide")
        analysis: Detailed analysis or advice with specific data and insights
    
    Returns:
        Dictionary with success status and document ID
    """
    if not LEGAL_API_ENDPOINT or not LEGAL_API_KEY:
        return {
            "success": False,
            "error": "Legal companion API not configured. Running in local mode."
        }
    
    document = {
        "text": analysis,
        "metadata": {
            "topic": topic,
            "timestamp": datetime.now(UTC).isoformat()
        }
    }
    
    try:
        result = ingest_with_retries(document)
        return {
            "success": True,
            "document_id": result.get("document_id"),  # Changed from documentId
            "message": f"Successfully ingested analysis for {topic}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }