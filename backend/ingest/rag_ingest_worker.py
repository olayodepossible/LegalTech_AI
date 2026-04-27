"""
SQS-triggered Lambda: process ``rag_document_ingest`` messages from POST /api/rag/documents/upload.

Downloads the object from S3, extracts text, chunks it, embeds via SageMaker, writes to S3 Vectors.
"""

from __future__ import annotations

import io
import json
import logging
import os
import time
import uuid
from datetime import datetime, UTC
from typing import Any

import boto3

from flow_log import log_flow, new_trace_id, trace_context

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger("legaltech.flow").setLevel(logging.INFO)

VECTOR_BUCKET = os.environ.get("VECTOR_BUCKET", "")
INDEX_NAME = os.environ.get("INDEX_NAME", "legal-research")
SAGEMAKER_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT", "")
CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_CHARS", "2400"))
CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "200"))

s3 = boto3.client("s3")
sagemaker_runtime = boto3.client("sagemaker-runtime")
s3_vectors = boto3.client("s3vectors")


def _get_embedding(text: str) -> list[float]:
    if not SAGEMAKER_ENDPOINT:
        raise RuntimeError("SAGEMAKER_ENDPOINT is not set")
    body = json.dumps({"inputs": text})
    t0 = time.perf_counter()
    log_flow(
        "downstream.start",
        step="sagemaker.invoke_endpoint",
        target="sagemaker",
        endpoint=SAGEMAKER_ENDPOINT,
        body_chars=len(text),
    )
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=body,
    )
    log_flow(
        "downstream.end",
        step="sagemaker.invoke_endpoint",
        target="sagemaker",
        endpoint=SAGEMAKER_ENDPOINT,
        duration_ms=(time.perf_counter() - t0) * 1000,
    )
    result = json.loads(response["Body"].read().decode())
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]
            return result[0]
    return result


def _extract_text(body: bytes, content_type: str, filename: str) -> str:
    ct = (content_type or "").lower()
    name = (filename or "").lower()

    if ct.startswith("text/") or name.endswith((".txt", ".md", ".csv", ".json")):
        return body.decode("utf-8", errors="replace")

    if "pdf" in ct or name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            raise RuntimeError("PDF support requires pypdf in the deployment package") from None
        reader = PdfReader(io.BytesIO(body))
        parts: list[str] = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                parts.append(t)
        return "\n\n".join(parts).strip() or ""

    raise RuntimeError(
        f"Unsupported type for RAG ingest: content_type={content_type!r} filename={filename!r}"
    )


def _chunks(text: str, size: int, overlap: int) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        piece = text[i : i + size]
        if piece.strip():
            out.append(piece.strip())
        i += max(1, size - overlap)
    return out


def _process_message(payload: dict[str, Any]) -> None:
    if payload.get("type") != "rag_document_ingest":
        logger.info("Skipping non-rag message type=%s", payload.get("type"))
        return

    bucket = payload.get("bucket") or VECTOR_BUCKET
    s3_key = payload.get("s3_key")
    if not bucket or not s3_key:
        raise ValueError("bucket and s3_key are required")

    clerk_user_id = str(payload.get("clerk_user_id") or "")
    document_id = str(payload.get("document_id") or "")
    original_filename = str(payload.get("original_filename") or "")
    content_type = str(payload.get("content_type") or "application/octet-stream")

    t_dl = time.perf_counter()
    log_flow(
        "downstream.start",
        step="s3.get_object",
        target="s3",
        bucket=bucket,
        key=s3_key[-200:] if len(s3_key) > 200 else s3_key,
        document_id=document_id,
    )
    obj = s3.get_object(Bucket=bucket, Key=s3_key)
    body = obj["Body"].read()
    log_flow(
        "downstream.end",
        step="s3.get_object",
        target="s3",
        duration_ms=(time.perf_counter() - t_dl) * 1000,
        bytes=len(body),
        document_id=document_id,
    )
    raw_text = _extract_text(body, content_type, original_filename)
    if not raw_text.strip():
        logger.warning("No text extracted for document_id=%s key=%s", document_id, s3_key)
        return

    parts = _chunks(raw_text, CHUNK_SIZE, CHUNK_OVERLAP)
    if not parts:
        return

    now = datetime.now(UTC).isoformat()
    vectors: list[dict[str, Any]] = []
    for idx, chunk in enumerate(parts):
        emb = _get_embedding(chunk[:8000])
        vid = str(uuid.uuid4())
        meta = {
            "text": chunk[:50000],
            "clerk_user_id": clerk_user_id,
            "document_id": document_id,
            "chunk_index": idx,
            "chunk_count": len(parts),
            "source_s3_key": s3_key,
            "original_filename": original_filename[:500],
            "ingest_kind": "user_rag_upload",
            "timestamp": now,
        }
        vectors.append(
            {
                "key": vid,
                "data": {"float32": emb},
                "metadata": meta,
            }
        )

    # Batch in groups of 10 to limit request size
    batch = 10
    for i in range(0, len(vectors), batch):
        batch_n = len(vectors[i : i + batch])
        tp = time.perf_counter()
        log_flow(
            "downstream.start",
            step="s3vectors.put_vectors",
            target="s3vectors",
            bucket=VECTOR_BUCKET,
            index=INDEX_NAME,
            batch_size=batch_n,
            batch_index=i // batch,
        )
        s3_vectors.put_vectors(
            vectorBucketName=VECTOR_BUCKET,
            indexName=INDEX_NAME,
            vectors=vectors[i : i + batch],
        )
        log_flow(
            "downstream.end",
            step="s3vectors.put_vectors",
            target="s3vectors",
            duration_ms=(time.perf_counter() - tp) * 1000,
            batch_size=batch_n,
        )
    logger.info(
        "RAG ingest ok document_id=%s chunks=%s user=%s...",
        document_id,
        len(vectors),
        clerk_user_id[:20] if clerk_user_id else "",
    )
    log_flow(
        "ingest.complete",
        step="rag_document_ingest",
        target="s3vectors",
        document_id=document_id,
        chunk_count=len(vectors),
    )


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if not VECTOR_BUCKET or not SAGEMAKER_ENDPOINT:
        logger.error("VECTOR_BUCKET or SAGEMAKER_ENDPOINT missing; cannot ingest")
        return {"batchItemFailures": []}

    aws_rid = getattr(context, "aws_request_id", None) if context else None
    failures: list[dict[str, str]] = []
    for record in event.get("Records", []):
        mid = record.get("messageId") or ""
        try:
            raw = record.get("body") or "{}"
            payload = json.loads(raw) if isinstance(raw, str) else raw
            api_tid = None
            if isinstance(payload, dict):
                api_tid = payload.get("api_trace_id")
            trace_id = (str(api_tid).strip() if api_tid else "") or mid or aws_rid or new_trace_id()
            with trace_context(trace_id, "rag_ingest_worker"):
                log_flow(
                    "sqs.record.start",
                    step="lambda.sqs",
                    target="process",
                    sqs_message_id=mid or None,
                    ingest_type=payload.get("type") if isinstance(payload, dict) else None,
                )
                _process_message(payload)
                log_flow(
                    "sqs.record.end",
                    step="lambda.sqs",
                    target="process",
                    sqs_message_id=mid or None,
                )
        except Exception as e:
            logger.exception("RAG ingest failed for message %s: %s", mid, e)
            with trace_context(trace_id, "rag_ingest_worker"):
                log_flow(
                    "sqs.record.error",
                    step="lambda.sqs",
                    target="process",
                    sqs_message_id=mid or None,
                    exc=e,
                    level=logging.ERROR,
                )
            if mid:
                failures.append({"itemIdentifier": mid})

    return {"batchItemFailures": failures}
