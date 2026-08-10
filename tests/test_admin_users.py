"""Authorization and least-privilege administration regression tests."""

import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from api.main import app
from api.services.entra_auth import EntraIdentity, require_entra_identity
from api.services.user_store import UserStore, UserStoreUnavailable


class AdminUsersApiTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "CHAT_ALLOW_LOCAL_DEV": "false",
            "CHAT_SESSION_SECRET": "admin-user-tests",
            "ALLOWED_EMAILS": "pedrohssoares@live.com",
        })
        self.environment.start()
        self.store = UserStore("sqlite:///:memory:")
        self.store_patch_auth = patch("api.services.chat_auth.user_store", self.store)
        self.store_patch_admin = patch("api.routers.admin.user_store", self.store)
        self.store_patch_auth.start()
        self.store_patch_admin.start()
        self.identity = EntraIdentity(
            email="pedrohssoares@live.com",
            object_id="owner-object",
            tenant_id="owner-tenant",
        )
        app.dependency_overrides[require_entra_identity] = lambda: self.identity
        self.acquire = patch("api.routers.chat.provider.acquire_session", new_callable=AsyncMock)
        self.acquire_mock = self.acquire.start()
        self.acquire_mock.return_value = {"available": True, "loaded": True}
        self.release = patch("api.routers.chat.provider.release_session", new_callable=AsyncMock)
        self.release_mock = self.release.start()
        self.release_mock.return_value = {"released": True}
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.pop(require_entra_identity, None)
        self.release.stop()
        self.acquire.stop()
        self.store_patch_admin.stop()
        self.store_patch_auth.stop()
        self.store.engine.dispose()
        self.environment.stop()

    def _login(self, identity: EntraIdentity | None = None) -> dict:
        if identity is not None:
            self.identity = identity
        response = self.client.post("/api/chat/session")
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    @staticmethod
    def _headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    def test_bootstrap_owner_and_public_user_contract(self):
        session = self._login()
        self.assertEqual(session["role"], "admin")
        self.assertIn("users:write", session["permissions"])
        self.assertTrue(session["is_owner"])

        response = self.client.get("/api/admin/users", headers=self._headers(session["token"]))
        self.assertEqual(response.status_code, 200)
        owner = response.json()["users"][0]
        self.assertEqual(owner["email"], "pedrohssoares@live.com")
        self.assertEqual(owner["role"], "admin")
        self.assertNotIn("entra_object_id", owner)
        self.assertNotIn("entra_tenant_id", owner)

    def test_invite_first_login_binding_member_is_least_privileged_and_disable_revokes(self):
        owner = self._login()
        owner_headers = self._headers(owner["token"])
        invited = self.client.post(
            "/api/admin/users",
            headers=owner_headers,
            json={"email": "Analista@Example.com", "role": "member"},
        )
        self.assertEqual(invited.status_code, 201, invited.text)
        invited_user = invited.json()["user"]
        self.assertEqual(invited_user["status"], "pending")

        member = self._login(EntraIdentity(
            email="analista@example.com",
            object_id="member-object",
            tenant_id="member-tenant",
        ))
        self.assertEqual(member["role"], "member")
        self.assertEqual(member["permissions"], ["chat:use"])
        member_headers = self._headers(member["token"])
        self.assertEqual(self.client.get("/api/admin/users", headers=member_headers).status_code, 403)
        self.assertEqual(self.client.get("/api/admin/usage", headers=member_headers).status_code, 403)

        disabled = self.client.patch(
            f"/api/admin/users/{invited_user['id']}",
            headers=owner_headers,
            json={"status": "disabled", "version": invited_user["version"]},
        )
        # First login does not change session_version, so the invitation version remains current.
        self.assertEqual(disabled.status_code, 200, disabled.text)
        self.assertEqual(disabled.json()["user"]["status"], "disabled")
        self.assertEqual(self.client.get("/api/context", headers=member_headers).status_code, 401)

    def test_bound_email_cannot_be_taken_over_by_a_different_entra_subject(self):
        owner = self._login()
        headers = self._headers(owner["token"])
        invited = self.client.post(
            "/api/admin/users", headers=headers,
            json={"email": "member@example.com", "role": "member"},
        )
        self.assertEqual(invited.status_code, 201)
        self._login(EntraIdentity(
            email="member@example.com", object_id="first-object", tenant_id="tenant-a",
        ))
        self.identity = EntraIdentity(
            email="member@example.com", object_id="attacker-object", tenant_id="tenant-b",
        )
        rejected = self.client.post("/api/chat/session")
        self.assertEqual(rejected.status_code, 403)
        self.assertEqual(rejected.json()["detail"], "Acesso não autorizado.")

    def test_owner_cannot_be_demoted_disabled_or_removed(self):
        owner = self._login()
        headers = self._headers(owner["token"])
        listed = self.client.get("/api/admin/users", headers=headers).json()["users"]
        owner_user = next(item for item in listed if item["is_owner"])
        for method, body in (("PATCH", {"role": "member"}), ("PATCH", {"status": "disabled"}), ("DELETE", None)):
            response = self.client.request(
                method,
                f"/api/admin/users/{owner_user['id']}",
                headers=headers,
                json=body,
            )
            self.assertEqual(response.status_code, 409, response.text)

    def test_logout_invalidates_the_backend_token(self):
        owner = self._login()
        headers = self._headers(owner["token"])
        ended = self.client.delete("/api/chat/session", headers=headers)
        self.assertEqual(ended.status_code, 200, ended.text)
        self.assertEqual(self.client.get("/api/context", headers=headers).status_code, 401)

    def test_duplicate_invite_and_stale_version_are_conflicts(self):
        owner = self._login()
        headers = self._headers(owner["token"])
        created = self.client.post(
            "/api/admin/users",
            headers=headers,
            json={"email": "duplicate@example.com", "role": "member"},
        )
        self.assertEqual(created.status_code, 201, created.text)
        duplicate = self.client.post(
            "/api/admin/users",
            headers=headers,
            json={"email": "DUPLICATE@example.com", "role": "member"},
        )
        self.assertEqual(duplicate.status_code, 409, duplicate.text)

        user = created.json()["user"]
        updated = self.client.patch(
            f"/api/admin/users/{user['id']}",
            headers=headers,
            json={"role": "admin", "version": user["version"]},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        stale = self.client.patch(
            f"/api/admin/users/{user['id']}",
            headers=headers,
            json={"role": "member", "version": user["version"]},
        )
        self.assertEqual(stale.status_code, 409, stale.text)

    def test_role_change_revokes_existing_session_and_relogin_uses_new_role(self):
        owner = self._login()
        owner_headers = self._headers(owner["token"])
        invitation = self.client.post(
            "/api/admin/users",
            headers=owner_headers,
            json={"email": "second-admin@example.com", "role": "admin"},
        ).json()["user"]
        identity = EntraIdentity(
            email="second-admin@example.com",
            object_id="second-admin-object",
            tenant_id="second-admin-tenant",
        )
        admin = self._login(identity)
        admin_headers = self._headers(admin["token"])
        self.assertEqual(self.client.get("/api/admin/users", headers=admin_headers).status_code, 200)

        demoted = self.client.patch(
            f"/api/admin/users/{invitation['id']}",
            headers=owner_headers,
            json={"role": "member", "version": invitation["version"]},
        )
        self.assertEqual(demoted.status_code, 200, demoted.text)
        self.assertEqual(self.client.get("/api/context", headers=admin_headers).status_code, 401)
        member = self._login(identity)
        self.assertEqual(member["role"], "member")
        self.assertEqual(
            self.client.get("/api/admin/users", headers=self._headers(member["token"])).status_code,
            403,
        )

    def test_soft_remove_preserves_record_and_audit_without_exposing_subject(self):
        owner = self._login()
        headers = self._headers(owner["token"])
        user = self.client.post(
            "/api/admin/users",
            headers=headers,
            json={"email": "removed@example.com", "role": "member"},
        ).json()["user"]

        removed = self.client.delete(
            f"/api/admin/users/{user['id']}?version={user['version']}",
            headers=headers,
        )
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(removed.json()["user"]["status"], "disabled")

        directory = self.client.get("/api/admin/users", headers=headers).json()["users"]
        retained = next(item for item in directory if item["id"] == user["id"])
        self.assertEqual(retained["status"], "disabled")
        self.assertNotIn("entra_object_id", retained)
        self.assertNotIn("entra_tenant_id", retained)

        audit = self.client.get("/api/admin/audit", headers=headers)
        self.assertEqual(audit.status_code, 200, audit.text)
        event = next(item for item in audit.json()["events"] if item["target_user_id"] == user["id"])
        self.assertEqual(event["action"], "user_access_removed")
        self.assertNotIn("entra_object_id", audit.text)
        self.assertNotIn("entra_tenant_id", audit.text)

    def test_authorization_database_failure_fails_closed(self):
        owner = self._login()
        headers = self._headers(owner["token"])
        with patch.object(
            self.store,
            "authorize_session",
            side_effect=UserStoreUnavailable("offline"),
        ):
            response = self.client.get("/api/context", headers=headers)
        self.assertEqual(response.status_code, 503)
        self.assertIn("temporariamente indisponível", response.json()["detail"])

    def test_usage_report_is_per_user_idempotent_and_does_not_expose_content(self):
        owner = self._login()
        headers = self._headers(owner["token"])
        owner_user = self.client.get("/api/admin/users", headers=headers).json()["users"][0]

        recorded = self.store.record_usage(
            response_id="response-generated",
            user_id=owner_user["id"],
            provider="openai",
            model="gpt-5.6-luna",
            response_mode="llm",
            analysis_mode="deep",
            usage={
                "input_tokens": 100,
                "output_tokens": 25,
                "reasoning_tokens": 10,
                "cached_tokens": 20,
            },
            cache_hit=False,
        )
        duplicate = self.store.record_usage(
            response_id="response-generated",
            user_id=owner_user["id"],
            provider="openai",
            model="gpt-5.6-luna",
            response_mode="llm",
            analysis_mode="deep",
            usage={"input_tokens": 999, "output_tokens": 999},
            cache_hit=False,
        )
        self.store.record_usage(
            response_id="response-cache-hit",
            user_id=owner_user["id"],
            provider="openai",
            model="gpt-5.6-luna",
            response_mode="llm",
            analysis_mode="deep",
            # Even if stale counters are replayed with a cache hit, they must
            # be treated as avoided work rather than new consumption.
            usage={"input_tokens": 100, "output_tokens": 25, "total_tokens": 125, "saved_tokens": 125},
            cache_hit=True,
        )
        self.store.record_usage(
            response_id="response-deterministic",
            user_id=owner_user["id"],
            provider="outputs",
            model=None,
            response_mode="deterministic",
            analysis_mode="fast",
            usage={},
            cache_hit=False,
        )

        self.assertTrue(recorded)
        self.assertFalse(duplicate)
        response = self.client.get("/api/admin/usage?days=30", headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        report = response.json()
        self.assertEqual(report["totals"]["requests"], 3)
        self.assertEqual(report["totals"]["generated_responses"], 1)
        self.assertEqual(report["totals"]["cache_hits"], 1)
        self.assertEqual(report["totals"]["input_tokens"], 100)
        self.assertEqual(report["totals"]["output_tokens"], 25)
        self.assertEqual(report["totals"]["total_tokens"], 125)
        self.assertEqual(report["totals"]["reasoning_tokens"], 10)
        self.assertEqual(report["totals"]["cached_tokens"], 20)
        self.assertEqual(report["totals"]["saved_tokens"], 125)
        self.assertNotIn("entra_object_id", response.text)
        self.assertNotIn("entra_tenant_id", response.text)
        self.assertNotIn("prompt", response.text.lower())


if __name__ == "__main__":
    unittest.main()
