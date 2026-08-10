"""Persistence, isolation, search and summarization tests for chat history."""

import unittest

from api.services.conversation_store import ConversationNotFound, ConversationStore


class ConversationStoreTests(unittest.TestCase):
    def setUp(self):
        self.store = ConversationStore("sqlite:///:memory:")
        self.context = {
            "route": "/gestao",
            "label": "GESTÃO",
            "filters": {"periodo": "ANO"},
        }

    def tearDown(self):
        self.store.engine.dispose()

    def append(self, owner: str, conversation_id: str, index: int = 1):
        return self.store.append_exchange(
            owner,
            conversation_id,
            f"Pergunta operacional {index} sobre P2",
            f"Resposta validada {index} sobre o risco de P2.",
            response_id=f"response-{owner}-{index}",
            metadata_value={"mode": "llm", "analysis_mode": "fast"},
            dashboard_context=self.context,
        )

    def test_owner_isolation_and_automatic_title(self):
        first = self.append("owner-a", "shared-id")
        second = self.append("owner-b", "shared-id")
        self.assertIn("Pergunta operacional 1", first["title"])
        self.assertEqual(first["message_count"], 2)
        self.assertEqual(second["message_count"], 2)
        self.assertEqual(len(self.store.list("owner-a")), 1)
        self.assertEqual(len(self.store.list("owner-b")), 1)

    def test_search_pin_rename_context_and_delete(self):
        self.append("owner", "conversation")
        self.assertEqual(len(self.store.list("owner", "operacional")), 1)
        updated = self.store.update(
            "owner",
            "conversation",
            title="Risco do primeiro trimestre",
            pinned=True,
            dashboard_context={
                "route": "/tecnico",
                "label": "TÉCNICO",
                "filters": {"cluster": "4"},
            },
        )
        self.assertTrue(updated["pinned"])
        self.assertEqual(updated["dashboard_context"]["route"], "/tecnico")
        self.assertEqual(len(self.store.list("owner", "primeiro trimestre")), 1)
        self.assertTrue(self.store.delete("owner", "conversation"))
        with self.assertRaises(ConversationNotFound):
            self.store.get("owner", "conversation")

    def test_long_conversation_creates_summary_but_keeps_full_archive(self):
        for index in range(1, 7):
            self.append("owner", "long", index)
        conversation = self.store.get("owner", "long")
        history = self.store.history("owner", "long")
        self.assertEqual(conversation["message_count"], 12)
        self.assertTrue(conversation["summary"].startswith("Resumo automático"))
        self.assertEqual(len(history), 7)
        self.assertTrue(history[0]["content"].startswith("Resumo automático"))

    def test_response_metadata_can_restore_feedback_authorization(self):
        self.append("owner", "conversation")
        metadata = self.store.response_metadata("owner", "response-owner-1")
        self.assertEqual(metadata["mode"], "llm")
        self.assertIsNone(self.store.response_metadata("other-owner", "response-owner-1"))


if __name__ == "__main__":
    unittest.main()
