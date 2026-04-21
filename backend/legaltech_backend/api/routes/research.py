from fastapi import APIRouter, Depends

from legaltech_backend.api.deps import get_research_service
from legaltech_backend.schemas.research import ResearchRequest, ResearchResponse
from legaltech_backend.services.research_service import ResearchService

router = APIRouter()


@router.post("/query", response_model=ResearchResponse)
async def legal_research(
    body: ResearchRequest,
    svc: ResearchService = Depends(get_research_service),
) -> ResearchResponse:
    data = await svc.research(
        body.query,
        jurisdiction=body.jurisdiction,
        language=body.language,
    )
    return ResearchResponse(**data)
