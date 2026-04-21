"""Prediction Service — orchestrates ML + optional LLM explanation (README flow)."""

from __future__ import annotations

import logging
from typing import Any

from legaltech_backend.integrations.llm import LLMClient
from legaltech_backend.services.ml_model_service import MLModelService

logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(self, ml: MLModelService, llm: LLMClient) -> None:
        self._ml = ml
        self._llm = llm

    async def predict_case(self, case: dict[str, Any], *, explain: bool = True) -> dict[str, Any]:
        prediction = self._ml.predict(case)
        result: dict[str, Any] = {"prediction": prediction, "explanation": None}
        if explain:
            system = (
                "You are a legal analytics assistant. Given structured prediction output, "
                "briefly explain the reasoning for a lawyer. Do not claim certainty."
            )
            user = f"Case summary: {case}\n\nModel output: {prediction}"
            result["explanation"] = await self._llm.complete(system, user)
        logger.info("prediction.complete explain=%s", explain)
        return result
