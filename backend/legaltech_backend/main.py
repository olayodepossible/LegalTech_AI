"""FastAPI application entry — composes gateway-style middleware and versioned routers."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from legaltech_backend import __version__
from legaltech_backend.api.middleware import RequestIDMiddleware
from legaltech_backend.api.routes import contracts, documents, health, ingestion, ml, predictions, rag, research
from legaltech_backend.config import get_settings
from legaltech_backend.integrations.llm import build_llm_client
from legaltech_backend.integrations.queue import StubQueueClient
from legaltech_backend.integrations.storage import StubStorageClient
from legaltech_backend.integrations.vector_store import StubVectorStoreClient
from legaltech_backend.logging_conf import configure_logging
from legaltech_backend.repositories.document_repository import DocumentRepository
from legaltech_backend.repositories.metadata_repository import MetadataRepository
from legaltech_backend.services.contract_service import ContractService
from legaltech_backend.services.document_service import DocumentService
from legaltech_backend.services.ingestion_service import IngestionService
from legaltech_backend.services.ml_model_service import MLModelService
from legaltech_backend.services.prediction_service import PredictionService
from legaltech_backend.services.rag_service import RAGService
from legaltech_backend.services.research_service import ResearchService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)

    doc_repo = DocumentRepository()
    meta_repo = MetadataRepository()
    storage = StubStorageClient(settings.s3_bucket)
    vector = StubVectorStoreClient(settings.vector_collection)
    queue = StubQueueClient()
    llm = build_llm_client(settings.llm_api_url, settings.llm_api_key)

    rag = RAGService(vector, llm, settings.vector_collection)
    document_service = DocumentService(doc_repo, storage)
    contract_service = ContractService(document_service, rag)
    research_service = ResearchService(rag)
    ml_model_service = MLModelService()
    prediction_service = PredictionService(ml_model_service, llm)
    ingestion_service = IngestionService(doc_repo, meta_repo, queue, rag)

    app.state.settings = settings
    app.state.contract_service = contract_service
    app.state.research_service = research_service
    app.state.prediction_service = prediction_service
    app.state.document_service = document_service
    app.state.rag_service = rag
    app.state.ingestion_service = ingestion_service
    app.state.ml_model_service = ml_model_service

    logger.info("startup complete version=%s", __version__)
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    v1 = settings.api_v1_prefix
    app.include_router(health.router, prefix=v1)
    app.include_router(contracts.router, prefix=f"{v1}/contracts", tags=["contracts"])
    app.include_router(research.router, prefix=f"{v1}/research", tags=["research"])
    app.include_router(predictions.router, prefix=f"{v1}/predictions", tags=["predictions"])
    app.include_router(ml.router, prefix=f"{v1}/ml", tags=["ml-model"])
    app.include_router(documents.router, prefix=f"{v1}/documents", tags=["documents"])
    app.include_router(rag.router, prefix=f"{v1}/rag", tags=["rag"])
    app.include_router(ingestion.router, prefix=f"{v1}/ingestion", tags=["ingestion"])

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run(
        "legaltech_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
