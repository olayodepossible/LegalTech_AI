from fastapi import APIRouter, Depends

from legaltech_backend.api.deps import get_contract_service
from legaltech_backend.schemas.contracts import ContractAnalyzeRequest, ContractAnalyzeResponse
from legaltech_backend.services.contract_service import ContractService

router = APIRouter()


@router.post("/analyze", response_model=ContractAnalyzeResponse)
async def analyze_contract(
    body: ContractAnalyzeRequest,
    svc: ContractService = Depends(get_contract_service),
) -> ContractAnalyzeResponse:
    data = await svc.analyze(
        query=body.query,
        doc_id=body.document_id,
        language=body.language,
    )
    return ContractAnalyzeResponse(
        summary=data["summary"],
        document_id=data["document_id"],
        retrieved_clauses=data["retrieved_clauses"],
        risks=data["risks"],
        suggestions=data["suggestions"],
    )
