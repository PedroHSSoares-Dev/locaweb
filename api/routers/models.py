"""Canonical model registry endpoints."""

from fastapi import APIRouter, HTTPException

from api.services.model_registry import ModelRegistryError, get_model_registry


router = APIRouter(tags=["Modelos"])


@router.get("/models/registry", summary="Registro canônico de modelos")
def model_registry():
    """Return active, shadow, exploratory and scenario-only model governance."""
    try:
        registry = get_model_registry()
    except ModelRegistryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"disponivel": True, **registry}
