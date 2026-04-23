"""
Tools for the Legal Companion Researcher agent
"""
import os
from typing import Dict, Any
from datetime import datetime, UTC
import httpx
from agents import function_tool
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuration from environment
LEGAL_API_ENDPOINT = os.getenv("LEGAL_API_ENDPOINT")
LEGAL_API_KEY = os.getenv("LEGAL_API_KEY")
SERPER_API_KEY = (os.getenv("SERPER_API_KEY") or "").strip()
SERPER_SEARCH_URL = (os.getenv("SERPER_SEARCH_URL") or "https://google.serper.dev/search").strip()


def serper_search_configured() -> bool:
    return bool(SERPER_API_KEY)


def _ingest(document: Dict[str, Any]) -> Dict[str, Any]:
    """Internal function to make the actual API call."""
    with httpx.Client() as client:
        response = client.post(
            LEGAL_API_ENDPOINT,
            json=document,
            headers={"x-api-key": LEGAL_API_KEY},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()


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
    if not SERPER_API_KEY:
        return (
            "Error: Serper is not configured (set SERPER_API_KEY in the environment for Google search)."
        )
    n = max(1, min(int(num_results), 15))
    try:
        with httpx.Client() as client:
            res = client.post(
                SERPER_SEARCH_URL,
                json={"q": query, "num": n},
                headers={
                    "X-API-KEY": SERPER_API_KEY,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
            text = res.text
            if not res.is_success:
                return f"Serper API error (HTTP {res.status_code}): {text[:2000]}"
            data = res.json()
    except Exception as e:
        return f"Serper request failed: {e}"

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