"""
Shared embedding + S3 Vectors write helpers for ingest HTTP Lambda and RAG SQS worker.
"""

from __future__ import annotations

import datetime
import json
import os
import uuid
from typing import Any, Dict, List

import boto3

VECTOR_BUCKET = os.environ.get("VECTOR_BUCKET", "legal-vectors")
SAGEMAKER_ENDPOINT = os.environ.get("SAGEMAKER_ENDPOINT")
INDEX_NAME = os.environ.get("INDEX_NAME", "legal-research")

sagemaker_runtime = boto3.client("sagemaker-runtime")
s3_vectors = boto3.client("s3vectors")


def get_embedding(text: str) -> List[float]:
    """Embedding vector from SageMaker (HuggingFace-style nested list)."""
    if not SAGEMAKER_ENDPOINT:
        raise RuntimeError("SAGEMAKER_ENDPOINT is not set")
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=SAGEMAKER_ENDPOINT,
        ContentType="application/json",
        Body=json.dumps({"inputs": text}),
    )
    result = json.loads(response["Body"].read().decode())
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list) and len(result[0]) > 0:
            if isinstance(result[0][0], list):
                return result[0][0]
            return result[0]
    return result


def put_vector(
    *,
    vector_id: str,
    embedding: List[float],
    metadata: Dict[str, Any],
) -> None:
    """Single vector write (metadata must include retrievable ``text`` for RAG)."""
    s3_vectors.put_vectors(
        vectorBucketName=VECTOR_BUCKET,
        indexName=INDEX_NAME,
        vectors=[
            {
                "key": vector_id,
                "data": {"float32": embedding},
                "metadata": {
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    **metadata,
                },
            }
        ],
    )


def new_vector_id() -> str:
    return str(uuid.uuid4())
