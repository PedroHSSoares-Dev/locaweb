"""Canonical operational snapshot for dashboard integrations and chatbot."""

from fastapi import APIRouter

from api.schemas import ContextResponse
from api.services.operational_context import build_operational_context

router = APIRouter(tags=["Contexto Chatbot"])


@router.get(
    "/context",
    response_model=ContextResponse,
    summary="Snapshot operacional canônico para integrações e chatbot",
)
def get_context():
    """Aggregate current read-only model artifacts into one stable contract."""
    return build_operational_context()
