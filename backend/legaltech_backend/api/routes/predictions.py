from fastapi import APIRouter, Depends

from legaltech_backend.api.deps import get_prediction_service
from legaltech_backend.schemas.predictions import PredictionRequest, PredictionResponse
from legaltech_backend.services.prediction_service import PredictionService

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def predict_case(
    body: PredictionRequest,
    svc: PredictionService = Depends(get_prediction_service),
) -> PredictionResponse:
    data = await svc.predict_case(body.case, explain=body.explain)
    return PredictionResponse(prediction=data["prediction"], explanation=data["explanation"])
