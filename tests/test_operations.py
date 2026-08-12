"""Closed-loop operations and canonical model registry regression tests."""

import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api.main import app
from api.services.entra_auth import EntraIdentity, require_entra_identity
from api.services.operational_queue_store import OperationalQueueStore
from api.services.user_store import UserStore


class OperationsApiTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "CHAT_ALLOW_LOCAL_DEV": "false",
            "CHAT_SESSION_SECRET": "operations-tests",
            "ALLOWED_EMAILS": "pedrohssoares@live.com",
        })
        self.environment.start()
        self.user_store = UserStore("sqlite:///:memory:")
        self.queue_store = OperationalQueueStore("sqlite:///:memory:")
        self.auth_store_patch = patch("api.services.chat_auth.user_store", self.user_store)
        self.operations_store_patch = patch(
            "api.routers.operations.operational_queue_store", self.queue_store
        )
        self.auth_store_patch.start()
        self.operations_store_patch.start()
        app.dependency_overrides[require_entra_identity] = lambda: EntraIdentity(
            email="pedrohssoares@live.com", object_id="owner-object", tenant_id="owner-tenant",
        )
        self.acquire = patch("api.routers.chat.provider.acquire_session", new_callable=AsyncMock)
        self.acquire.start().return_value = {"available": True, "loaded": True}
        self.client = TestClient(app)
        session = self.client.post("/api/chat/session").json()
        self.headers = {"Authorization": f"Bearer {session['token']}"}

    def tearDown(self):
        app.dependency_overrides.pop(require_entra_identity, None)
        self.acquire.stop()
        self.operations_store_patch.stop()
        self.auth_store_patch.stop()
        self.queue_store.engine.dispose()
        self.user_store.engine.dispose()
        self.environment.stop()

    def test_registry_has_one_active_and_one_shadow_per_operational_task(self):
        response = self.client.get("/api/models/registry", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        models = response.json()["models"]
        for task in ("volume_d1_d7", "ola_risk_triage"):
            selected = [item for item in models if item["task"] == task]
            self.assertEqual(sum(item["status"] == "active" for item in selected), 1)
            self.assertGreaterEqual(sum(item["status"] == "shadow" for item in selected), 1)

    def test_public_forecasts_reconcile_total_and_priority_segments(self):
        for endpoint in ("/api/previsoes/d1", "/api/previsoes/d7"):
            with self.subTest(endpoint=endpoint):
                body = self.client.get(endpoint, headers=self.headers).json()
                self.assertEqual(body["total"], body["p2"] + body["p3"])
        series = self.client.get("/api/previsoes/serie", headers=self.headers).json()["serie"]
        self.assertEqual(len(series), 7)
        self.assertTrue(all(item["total"] == item["P2"] + item["P3"] for item in series))

    def test_alert_requires_observed_feedback_before_closing(self):
        created = self.client.post(
            "/api/operations/alerts", headers=self.headers,
            json={
                "title": "Validar pressão no Cluster 4", "priority": "P2",
                "source_model_id": "risk_linear_svm_structured_v1", "risk_score": 0.72,
                "team": "Team07", "recommended_action": "Cruzar escala e reconhecimento.",
            },
        )
        self.assertEqual(created.status_code, 201, created.text)
        alert = created.json()["alert"]
        rejected = self.client.patch(
            f"/api/operations/alerts/{alert['id']}", headers=self.headers,
            json={"status": "resolved", "version": alert["version"]},
        )
        self.assertEqual(rejected.status_code, 409, rejected.text)
        resolved = self.client.patch(
            f"/api/operations/alerts/{alert['id']}", headers=self.headers,
            json={
                "status": "resolved", "action_taken": "Escala revisada.",
                "observed_result": "Cobertura confirmada; sem violação observada.",
                "version": alert["version"],
            },
        )
        self.assertEqual(resolved.status_code, 200, resolved.text)
        self.assertEqual(resolved.json()["alert"]["status"], "resolved")
        audit = self.client.get(
            f"/api/operations/alerts/{alert['id']}/audit", headers=self.headers
        )
        self.assertEqual(audit.status_code, 200, audit.text)
        self.assertEqual(
            {event["action"] for event in audit.json()["events"]},
            {"alert_created", "alert_updated"},
        )

    def test_unknown_model_source_is_rejected(self):
        response = self.client.post(
            "/api/operations/alerts", headers=self.headers,
            json={"title": "Tentativa sem governança", "priority": "P3", "source_model_id": "modelo_inventado"},
        )
        self.assertEqual(response.status_code, 422, response.text)


if __name__ == "__main__":
    unittest.main()
