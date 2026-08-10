"""Focused regression tests for the chatbot runtime features."""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

from api.services.chat_auth import RateLimitError, enforce_rate_limit
from api.services.chat_cache import ResponseCache, context_fingerprint, response_cache_key
from api.services.chat_runtime import ConversationMemory, FeedbackRegistry
from api.services.ollama_provider import GenerationResult
from api.services.openai_provider import OpenAIProvider


class VersionedCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "CHAT_CACHE_ENABLED": "true",
            "CHAT_SEMANTIC_CACHE_ENABLED": "true",
            "CHAT_SEMANTIC_CACHE_THRESHOLD": "0.94",
        })
        self.environment.start()
        self.cache = ResponseCache()
        self.context = {"dataset": {"end": "2025-12-31"}, "forecast": {"d1": 66}}
        self.fingerprint = context_fingerprint(
            self.context,
            prompt_version="v1",
            provider="openai",
            model="luna",
        )

    def tearDown(self):
        self.environment.stop()

    def test_fingerprint_changes_with_context_prompt_and_model(self):
        changed_context = context_fingerprint(
            {**self.context, "forecast": {"d1": 67}},
            prompt_version="v1",
            provider="openai",
            model="luna",
        )
        changed_prompt = context_fingerprint(
            self.context,
            prompt_version="v2",
            provider="openai",
            model="luna",
        )
        self.assertNotEqual(self.fingerprint, changed_context)
        self.assertNotEqual(self.fingerprint, changed_prompt)

    async def test_exact_and_semantic_hits_preserve_sensitive_tokens(self):
        key = response_cache_key(
            namespace="user-a",
            message="Qual é o risco de P2 em 2026?",
            history=[],
            analysis_mode="fast",
            fingerprint=self.fingerprint,
        )
        value = {"reply": "Risco moderado.", "reasoning": "", "sources": [], "usage": {}}
        await self.cache.set(
            key,
            value,
            namespace="user-a",
            message="Qual é o risco de P2 em 2026?",
            history=[],
            analysis_mode="fast",
            fingerprint=self.fingerprint,
        )
        exact = await self.cache.get(
            key,
            namespace="user-a",
            message="Qual é o risco de P2 em 2026?",
            history=[],
            analysis_mode="fast",
            fingerprint=self.fingerprint,
        )
        self.assertEqual(exact.kind, "exact")

        semantic = await self.cache.get(
            "different-key",
            namespace="user-a",
            message="Qual e o risco de P2 em 2026",
            history=[],
            analysis_mode="fast",
            fingerprint=self.fingerprint,
        )
        self.assertEqual(semantic.kind, "semantic")

        changed_priority = await self.cache.get(
            "another-key",
            namespace="user-a",
            message="Qual e o risco de P3 em 2026",
            history=[],
            analysis_mode="fast",
            fingerprint=self.fingerprint,
        )
        self.assertIsNone(changed_priority)

        negated = await self.cache.get(
            "negated-key",
            namespace="user-a",
            message="Qual nao e o risco de P2 em 2026",
            history=[],
            analysis_mode="fast",
            fingerprint=self.fingerprint,
        )
        self.assertIsNone(negated)

    async def test_singleflight_coalesces_equal_generation_pattern(self):
        calls = 0

        async def work():
            nonlocal calls
            lookup = await self.cache.get(
                "flight-key",
                namespace="user-a",
                message="Analise o risco operacional consolidado",
                history=[],
                analysis_mode="fast",
                fingerprint=self.fingerprint,
            )
            if lookup:
                return lookup.value
            async with self.cache.singleflight("same"):
                lookup = await self.cache.get(
                    "flight-key",
                    namespace="user-a",
                    message="Analise o risco operacional consolidado",
                    history=[],
                    analysis_mode="fast",
                    fingerprint=self.fingerprint,
                    count_miss=False,
                )
                if lookup:
                    return lookup.value
                calls += 1
                await asyncio.sleep(0.01)
                value = {"reply": "Uma geração", "reasoning": "", "sources": [], "usage": {}}
                await self.cache.set(
                    "flight-key",
                    value,
                    namespace="user-a",
                    message="Analise o risco operacional consolidado",
                    history=[],
                    analysis_mode="fast",
                    fingerprint=self.fingerprint,
                )
                return value

        first, second = await asyncio.gather(work(), work())
        self.assertEqual(calls, 1)
        self.assertEqual(first["reply"], second["reply"])
        self.assertEqual(self.cache.stats["singleflight_waits"], 1)


class RuntimeStateTests(unittest.IsolatedAsyncioTestCase):
    async def test_conversation_memory_is_isolated_and_clearable(self):
        memory = ConversationMemory()
        await memory.append_exchange("user-a", "conversation", "Pergunta", "Resposta A")
        await memory.append_exchange("user-b", "conversation", "Pergunta", "Resposta B")
        self.assertEqual((await memory.get("user-a", "conversation"))[-1]["content"], "Resposta A")
        self.assertEqual((await memory.get("user-b", "conversation"))[-1]["content"], "Resposta B")
        await memory.clear("user-a", "conversation")
        self.assertEqual(await memory.get("user-a", "conversation"), [])

    async def test_feedback_requires_the_same_identity(self):
        registry = FeedbackRegistry()
        await registry.register("response-1", "user-a", {"provider": "openai"})
        self.assertFalse(await registry.submit("response-1", "user-b", "up"))
        self.assertTrue(await registry.submit("response-1", "user-a", "up"))


class ProviderModeTests(unittest.IsolatedAsyncioTestCase):
    def test_generation_result_remains_tuple_compatible(self):
        result = GenerationResult("Resposta", "Resumo", ({"id": "x", "label": "X", "kind": "tool"},), {})
        answer, reasoning = result
        self.assertEqual((answer, reasoning), ("Resposta", "Resumo"))

    def test_deep_mode_increases_reasoning_and_output_budget(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "test",
            "OPENAI_REASONING_EFFORT": "low",
            "OPENAI_DEEP_REASONING_EFFORT": "medium",
            "OPENAI_MAX_OUTPUT_TOKENS": "800",
            "OPENAI_DEEP_MAX_OUTPUT_TOKENS": "2200",
        }):
            provider = OpenAIProvider()
        fast = provider._payload("Analise o risco", [], {}, stream=False)
        deep = provider._payload("Analise o risco", [], {}, stream=False, analysis_mode="deep")
        self.assertEqual(fast["reasoning"], {"effort": "low"})
        self.assertEqual(deep["reasoning"], {"effort": "medium"})
        self.assertGreater(deep["max_output_tokens"], fast["max_output_tokens"])

    async def test_distributed_rate_limit_rejects_above_limit(self):
        with (
            patch.dict(os.environ, {"CHAT_RATE_LIMIT_PER_MINUTE": "2"}),
            patch(
                "api.services.chat_auth.shared_redis.increment_window",
                new=AsyncMock(side_effect=[1, 2, 3]),
            ),
        ):
            await enforce_rate_limit("user@example.com")
            await enforce_rate_limit("user@example.com")
            with self.assertRaises(RateLimitError):
                await enforce_rate_limit("user@example.com")


if __name__ == "__main__":
    unittest.main()
