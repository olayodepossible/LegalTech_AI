"""FastAPI dependencies — services resolved from app.state (wired in lifespan)."""

from __future__ import annotations

from fastapi import Request

from legaltech_backend.services.contract_service import ContractService
from legaltech_backend.services.document_service import DocumentService
from legaltech_backend.services.ingestion_service import IngestionService
from legaltech_backend.services.ml_model_service import MLModelService
from legaltech_backend.services.prediction_service import PredictionService
from legaltech_backend.services.rag_service import RAGService
from legaltech_backend.services.research_service import ResearchService


def get_contract_service(request: Request) -> ContractService:
    return request.app.state.contract_service


def get_research_service(request: Request) -> ResearchService:
    return request.app.state.research_service


def get_prediction_service(request: Request) -> PredictionService:
    return request.app.state.prediction_service


def get_document_service(request: Request) -> DocumentService:
    return request.app.state.document_service


def get_rag_service(request: Request) -> RAGService:
    return request.app.state.rag_service


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service


def get_ml_service(request: Request) -> MLModelService:
    return request.app.state.ml_model_service
