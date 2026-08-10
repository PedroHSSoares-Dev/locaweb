"""Select the analytical chatbot provider through environment configuration."""

from __future__ import annotations

import os

from api.services.ollama_provider import OllamaProvider, ProviderError
from api.services.openai_provider import OpenAIProvider


def build_llm_provider() -> OllamaProvider | OpenAIProvider:
    provider = os.getenv("CHAT_LLM_PROVIDER", "ollama").strip().lower()
    if provider == "openai":
        return OpenAIProvider()
    if provider == "ollama":
        return OllamaProvider()
    raise ProviderError(
        f"CHAT_LLM_PROVIDER inválido: `{provider}`. Use `openai` ou `ollama`."
    )
