from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    case: dict = Field(default_factory=dict, description="Arbitrary case payload for feature extraction")
    explain: bool = True


class PredictionResponse(BaseModel):
    prediction: dict
    explanation: str | None
