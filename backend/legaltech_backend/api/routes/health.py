from fastapi import APIRouter, Request

from legaltech_backend import __version__
from legaltech_backend.schemas.common import MessageResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=MessageResponse)
async def health() -> MessageResponse:
    return MessageResponse(message="ok", version=__version__)


@router.get("/ready", response_model=MessageResponse)
async def ready(request: Request) -> MessageResponse:
    _ = request.app.state  # services wired
    return MessageResponse(message="ready", version=__version__)
