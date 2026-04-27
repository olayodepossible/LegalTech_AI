"""
Retrieve user-scoped RAG chunks from S3 Vectors for legal chat context.

Requires env: VECTOR_BUCKET, INDEX_NAME, SAGEMAKER_ENDPOINT (same embedding model as ingest).
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.flow_log import log_flow

logger = logging.getLogger(__name__)

_aws_region = os.environ.get("AWS_REGION") or os.environ.get("DEFAULT_AWS_REGION") or "us-east-1"
_sagemaker = boto3.client("sagemaker-runtime", region_name=_aws_region)
_s3v = boto3.client("s3vectors", region_name=_aws_region)


def _configured() -> bool:
    return bool(
        (os.getenv("VECTOR_BUCKET") or "").strip()
        and (os.getenv("INDEX_NAME") or "").strip()
        and (os.getenv("SAGEMAKER_ENDPOINT") or "").strip()
    )


def _embed_query(text: str) -> list[float]:
    ep = (os.getenv("SAGEMAKER_ENDPOINT") or "").strip()
    body = json.dumps({"inputs": text})
    t0 = time.perf_counter()
    log_flow(
        "downstream.start",
        step="sagemaker.invoke_endpoint",
        target="sagemaker",
        endpoint=ep,
        body_chars=len(text),
    )
    try:
        r = _sagemaker.invoke_endpoint(
            EndpointName=ep,
            ContentType="application/json",
            Body=body,
        )
    except Exception as exc:
        log_flow(
            "downstream.error",
            step="sagemaker.invoke_endpoint",
            target="sagemaker",
            endpoint=ep,
            duration_ms=(time.perf_counter() - t0) * 1000,
            exc=exc,
            level=logging.ERROR,
        )
        raise
    log_flow(
        "downstream.end",
        step="sagemaker.invoke_endpoint",
        target="sagemaker",
        endpoint=ep,
        duration_ms=(time.perf_counter() - t0) * 1000,
    )
    result = json.loads(r["Body"].read().decode())
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]
            return result[0]
    return result  # type: ignore[return-value]


def retrieve_user_rag_context(
    clerk_user_id: str,
    user_message: str,
    *,
    top_k_query: int = 24,
    top_k_return: int = 6,
) -> str:
    """
    Return a markdown string of relevant chunks for this user, or empty string.
    """
    if not _configured() or not clerk_user_id or not (user_message or "").strip():
        return ""

    bucket = (os.getenv("VECTOR_BUCKET") or "").strip()
    index = (os.getenv("INDEX_NAME") or "").strip()
    try:
        qv = _embed_query(user_message[:8000])
        tq = time.perf_counter()
        log_flow(
            "downstream.start",
            step="s3vectors.query_vectors",
            target="s3vectors",
            bucket=bucket,
            index=index,
            top_k=top_k_query,
        )
        resp = _s3v.query_vectors(
            vectorBucketName=bucket,
            indexName=index,
            queryVector={"float32": qv},
            topK=top_k_query,
            returnDistance=True,
            returnMetadata=True,
        )
        raw_vecs = resp.get("vectors") or []
        log_flow(
            "downstream.end",
            step="s3vectors.query_vectors",
            target="s3vectors",
            bucket=bucket,
            index=index,
            duration_ms=(time.perf_counter() - tq) * 1000,
            raw_hit_count=len(raw_vecs),
        )
    except ClientError as e:
        log_flow(
            "downstream.error",
            step="s3vectors.query_vectors",
            target="s3vectors",
            bucket=bucket,
            index=index,
            exc=e,
            level=logging.WARNING,
        )
        logger.warning("RAG query_vectors failed: %s", e)
        return ""
    except Exception as e:
        log_flow(
            "downstream.error",
            step="rag.retrieve",
            target="s3vectors",
            exc=e,
            level=logging.WARNING,
        )
        logger.warning("RAG retrieval failed: %s", e)
        return ""

    vecs = raw_vecs
    out: list[dict[str, Any]] = []
    for v in vecs:
        meta = (v.get("metadata") or {}) if isinstance(v, dict) else {}
        if (meta.get("clerk_user_id") or "") != clerk_user_id:
            continue
        if (meta.get("ingest_kind") or "") != "user_rag_upload":
            continue
        text = (meta.get("text") or "").strip()
        if not text:
            continue
        out.append(
            {
                "text": text,
                "distance": v.get("distance"),
                "document_id": meta.get("document_id"),
                "filename": meta.get("original_filename") or "",
            }
        )
        if len(out) >= top_k_return:
            break

    log_flow(
        "rag.chunks.selected",
        step="rag.filter_metadata",
        target="s3vectors",
        chunks_after_user_filter=len(out),
    )
    if not out:
        return ""

    lines = [
        "The following passages were retrieved from **your uploaded documents** (semantic search).",
        "Use them when they help answer the question; if they are not relevant, rely on your legal research tools.",
        "",
    ]
    for i, item in enumerate(out, 1):
        fn = item.get("filename") or "document"
        doc = item.get("document_id") or ""
        lines.append(f"**Excerpt {i}** (file: {fn}, id: {doc})")
        lines.append(item["text"][:12000])
        lines.append("")
    return "\n".join(lines).strip()
