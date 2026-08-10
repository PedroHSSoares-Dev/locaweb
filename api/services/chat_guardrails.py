"""Deterministic input and output guardrails for the operational chatbot."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailDecision:
    category: str
    reply: str


@dataclass(frozen=True)
class GuardedOutput:
    reply: str
    reasoning: str
    blocked: bool = False
    category: str | None = None


CONFIDENTIAL_REQUEST_REPLY = (
    "Não posso fornecer instruções internas, contexto bruto, credenciais, arquivos internos "
    "ou identificadores sensíveis. Posso explicar capacidades, limitações e resultados "
    "operacionais agregados do Predictfy."
)

INSTRUCTION_OVERRIDE_REPLY = (
    "Essa solicitação não altera o funcionamento nem as regras do assistente. Posso continuar "
    "com uma análise de AIOps baseada nos dados operacionais autorizados."
)

OUT_OF_SCOPE_REPLY = (
    "Posso ajudar apenas com o escopo AIOps do Predictfy: incidentes, OLA, KPIs, previsões, "
    "modelos, clusters e priorização operacional."
)

EXTERNAL_CHANNEL_REPLY = (
    "Não posso criar ou reproduzir links, imagens ou canais externos destinados a transportar "
    "dados do contexto. Posso apresentar a análise diretamente nesta conversa."
)

OUTPUT_BLOCKED_REPLY = (
    "A resposta foi bloqueada porque continha uma forma insegura de apresentar contexto interno "
    "ou dados por um canal externo. Reformule a pergunta dentro do escopo operacional."
)


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


_CONFIDENTIAL_PATTERNS = tuple(re.compile(pattern) for pattern in (
    r"prompt\s+(?:de\s+)?sistema",
    r"instru(?:cao|coes)\s+(?:internas?|ocultas?|de\s+sistema)",
    r"(?:repita|imprima|revele|recite|traduza).*(?:veio\s+acima|instru(?:cao|coes)|contexto)",
    r"quantas?\s+(?:linhas|secoes).*(?:prompt|instru(?:cao|coes))",
    r"primeir[ao]\s+(?:palavra|secao).*(?:prompt|instru(?:cao|coes))",
    r"topicos?.*(?:proibid|restri(?:cao|coes)\s+internas)",
    r"payload\s+json",
    r"contexto\s+(?:bruto|completo|integral|interno)",
    r"arquivos?\s+de\s+contexto",
    r"exporte?.*\.json",
    r"risco_ola\.json",
    r"estrutura\s+de\s+diretorios",
    r"(?:codigo\s+fonte|source\s+code)",
    r"(?:mostre|mande|envie|imprima|revele).*(?:seu\s+codigo|implementacao\s+interna)",
    r"variaveis?\s+de\s+ambiente",
    r"chaves?\s+de\s+api",
    r"dados\s+brutos",
    r"(?:campo\s+)?debug.*contexto",
    r"nomes?\s+d[eo]s?\s+clientes?",
    r"ids?\s+d[eo]s?\s+tickets?",
    r"hostnames?",
    r"enderecos?\s+ip",
    r"dados\s+de\s+clientes?",
))

_OVERRIDE_PATTERNS = tuple(re.compile(pattern) for pattern in (
    r"ignore.*instru(?:cao|coes)",
    r"ignore.*(?:contexto|dados\s+oficiais|valores\s+oficiais)",
    r"esqueca.*(?:predictfy|instru(?:cao|coes)|regra)",
    r"(?:modo|nivel)\s+(?:dev|interno|irrestrito|sem\s+restri)",
    r"\[\s*sistema\s*\]",
    r"decodifique\s+e\s+execute",
    r"a\s+partir\s+de\s+agora.*(?:assistente|encerre\s+toda\s+resposta)",
    r"voce\s+agora\s+e\s+um\s+assistente",
))

_OUT_OF_SCOPE_PATTERNS = tuple(re.compile(pattern) for pattern in (
    r"(?:escreva|escrever|redija).*(?:e-?mail|poema|conto|ficcao)",
    r"assistente\s+(?:generico|do\s+google)",
    r"receita\s+(?:culinaria|de\s+comida)",
))

_URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)


def guard_user_message(message: str) -> GuardrailDecision | None:
    """Block requests that must not reach either the data context or the model."""
    text = _normalize(message)

    if _URL_PATTERN.search(message):
        return GuardrailDecision("external_channel", EXTERNAL_CHANNEL_REPLY)

    if any(pattern.search(text) for pattern in _CONFIDENTIAL_PATTERNS):
        return GuardrailDecision("confidential_request", CONFIDENTIAL_REQUEST_REPLY)

    if any(pattern.search(text) for pattern in _OVERRIDE_PATTERNS):
        return GuardrailDecision("instruction_override", INSTRUCTION_OVERRIDE_REPLY)

    requests_everything = (
        ("use todos" in text or "usar todos" in text)
        and any(term in text for term in ("dados", "contexto", "informacoes"))
    ) or "mais dados do que esta usando" in text
    if requests_everything:
        return GuardrailDecision("scope_expansion", CONFIDENTIAL_REQUEST_REPLY)

    if any(pattern.search(text) for pattern in _OUT_OF_SCOPE_PATTERNS):
        return GuardrailDecision("out_of_scope", OUT_OF_SCOPE_REPLY)

    return None


_UNSAFE_OUTPUT_PATTERNS = tuple(re.compile(pattern, re.IGNORECASE) for pattern in (
    r"https?://",
    r"!\s*\[[^\]]*\]\s*\(",
    r"\[[^\]]+\]\s*\(\s*(?:https?://|www\.)",
    r"[\"']debug[\"']\s*:",
    r"\bINJETADO\s*:",
    r"SOURCE AND INSTRUCTION PRIORITY",
    r"OFFICIAL OPERATIONAL CONTEXT",
    r"<official_data>",
    r"SYSTEM_PROMPT\s*=",
    r"\bsk-(?:proj-)?[A-Za-z0-9_-]{12,}",
    r"(?:OPENAI|GEMINI|GROQ|CHAT)_API_KEY",
    r"/(?:Users|home)/[^\s]+",
))


def _unsafe_output_category(value: str) -> str | None:
    for pattern in _UNSAFE_OUTPUT_PATTERNS:
        if pattern.search(value):
            return pattern.pattern
    return None


def guard_model_output(reply: str, reasoning: str = "") -> GuardedOutput:
    """Fail closed before any model-generated content reaches the client."""
    reply_category = _unsafe_output_category(reply)
    if reply_category:
        return GuardedOutput(
            reply=OUTPUT_BLOCKED_REPLY,
            reasoning="A validação de saída removeu conteúdo incompatível com a política de segurança.",
            blocked=True,
            category=reply_category,
        )

    if _unsafe_output_category(reasoning):
        reasoning = (
            "Foram consultadas somente evidências operacionais agregadas; detalhes internos "
            "foram omitidos pela validação de saída."
        )

    return GuardedOutput(reply=reply.strip(), reasoning=reasoning.strip())
