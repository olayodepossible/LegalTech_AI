"""ML Model Service surface (health / metadata). Inference is via /predictions/predict."""

from fastapi import APIRouter, Depends

from legaltech_backend.api.deps import get_ml_service
from legaltech_backend.services.ml_model_service import MLModelService

router = APIRouter()


@router.get("/health")
async def ml_health(ml: MLModelService = Depends(get_ml_service)) -> dict:
    return {"model": "stub-rules-v1", "status": "loaded", "service": "ml-model"}
