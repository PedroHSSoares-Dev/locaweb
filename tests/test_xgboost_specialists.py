"""Fast unit tests for the dependency-free specialist promotion gates."""
from __future__ import annotations

import unittest

from src.models.specialist_policy import promotion_decision


def _cv(score: float) -> dict:
    return {"score_robusto": score}


def _evaluation(q3_pr: float, q4_pr: float, q4_f1: float) -> dict:
    return {
        "validation_q3": {"ranking": {"pr_auc": q3_pr}},
        "test_q4": {
            "ranking": {"pr_auc": q4_pr},
            "threshold": {"f1": q4_f1},
        },
    }


class SpecialistPromotionPolicyTests(unittest.TestCase):
    def test_p2_cannot_auto_promote_with_too_few_positive_examples(self):
        result = promotion_decision(
            "P2",
            22,
            _cv(0.20),
            _cv(0.10),
            _evaluation(0.20, 0.20, 0.20),
            _evaluation(0.10, 0.10, 0.10),
        )
        self.assertEqual(result["status"], "challenger_experimental_amostra_insuficiente")

    def test_p3_promotes_only_when_all_predeclared_gates_win(self):
        promoted = promotion_decision(
            "P3",
            119,
            _cv(0.20),
            _cv(0.10),
            _evaluation(0.20, 0.20, 0.20),
            _evaluation(0.10, 0.10, 0.10),
        )
        self.assertEqual(promoted["status"], "promover_especialista")
        self.assertTrue(all(promoted["gates_vencidos"].values()))

    def test_p3_stays_on_generalist_when_final_period_regresses(self):
        retained = promotion_decision(
            "P3",
            119,
            _cv(0.20),
            _cv(0.10),
            _evaluation(0.20, 0.09, 0.09),
            _evaluation(0.10, 0.10, 0.10),
        )
        self.assertEqual(retained["status"], "manter_generalista")
        self.assertFalse(retained["gates_vencidos"]["q4_pr_auc"])
