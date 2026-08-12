"""Dependency-free promotion policy for OLA-risk specialist models."""
from __future__ import annotations

from typing import Any


def promotion_decision(
    priority: str,
    train_positives: int,
    specialist_cv: dict[str, Any],
    general_cv: dict[str, Any],
    specialist_evaluation: dict[str, Any],
    general_evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Apply evidence gates; P2 cannot auto-promote under 50 positives."""
    comparisons = {
        "cv_score_robusto": (
            specialist_cv["score_robusto"] - general_cv["score_robusto"]
        ),
        "q3_pr_auc": (
            specialist_evaluation["validation_q3"]["ranking"]["pr_auc"]
            - general_evaluation["validation_q3"]["ranking"]["pr_auc"]
        ),
        "q4_pr_auc": (
            specialist_evaluation["test_q4"]["ranking"]["pr_auc"]
            - general_evaluation["test_q4"]["ranking"]["pr_auc"]
        ),
        "q4_f1": (
            specialist_evaluation["test_q4"]["threshold"]["f1"]
            - general_evaluation["test_q4"]["threshold"]["f1"]
        ),
    }
    wins = {name: delta > 0 for name, delta in comparisons.items()}
    if priority == "P2" and train_positives < 50:
        status = "challenger_experimental_amostra_insuficiente"
        reason = f"P2 possui apenas {train_positives} violações no treino; promoção automática bloqueada."
    elif all(wins.values()):
        status = "promover_especialista"
        reason = "Especialista venceu o generalista em CV, Q3, Q4 e F1 operacional."
    else:
        status = "manter_generalista"
        reason = "Especialista não venceu o generalista em todos os gates predefinidos."
    return {
        "status": status,
        "motivo": reason,
        "deltas_especialista_menos_generalista": comparisons,
        "gates_vencidos": wins,
    }
