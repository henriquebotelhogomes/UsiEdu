"""Guardrails contra prompt injection e proteção de dados PII (T9.3 / PRD v4).

Três camadas de defesa com heurísticas determinísticas (regex) e
sanitização de dados pessoais (PII Masking):

1. **Ingestão:** cada chunk passa por :func:`detect_injection`; chunks
   sinalizados ganham ``suspicious=true`` e são **excluídos do índice**
   com log de auditoria (integrado em ``src/rag/ingest.py``).
2. **Entrada do usuário:** :func:`mask_pii` sanitiza CPF, cartões e telefones
   para evitar vazamento em logs e vetores; o detector de injeção monitora
   comportamentos suspeitos no trace.
3. **Saída:** :func:`validate_answer` verifica se a resposta final ecoa o
   prompt de sistema, ecoa instruções de jailbreak ou tenta alterar o
   comportamento do usuário ("a partir de agora..."). Se insegura, é
   substituída por :data:`RESPOSTA_SEGURA_PADRAO`.
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# --- PII (Personally Identifiable Information) Patterns (RF4-03) ---

PADROES_PII: dict[str, tuple[re.Pattern[str], str]] = {
    "cpf": (
        re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
        "[CPF_PROTEGIDO]",
    ),
    "cartao_credito": (
        re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
        "[CARTAO_PROTEGIDO]",
    ),
    "telefone": (
        re.compile(r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\s?\d{4}|\d{4})[-\s]?\d{4}\b"),
        "[TELEFONE_PROTEGIDO]",
    ),
}


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Identifica e ofusca dados pessoais sensíveis (PII) do texto.

    Args:
        text: Texto de entrada.

    Returns:
        Tupla contendo o texto sanitizado e a lista de tipos de PII encontrados.
    """
    detected_types: list[str] = []
    sanitized_text = text

    for pii_type, (pattern, replacement) in PADROES_PII.items():
        if pattern.search(sanitized_text):
            detected_types.append(pii_type)
            sanitized_text = pattern.sub(replacement, sanitized_text)

    return sanitized_text, detected_types


# --- Camadas 1 e 2: padrões de injeção (ingestão + entrada do usuário) ---

PADROES_INJECAO: dict[str, re.Pattern[str]] = {
    # "ignore as instruções (anteriores)", "ignorar as instruções", etc.
    "ignorar_instrucoes": re.compile(
        r"(ignorem?|ignorar|desconsider(?:e|ar)|esque[çc](?:a|ar))\s+(?:todas\s+)?(?:as\s+)?"
        r"instru[çc][õo]es",
        re.IGNORECASE,
    ),
    # "you are now ...", "agora você é ..."
    "nova_identidade": re.compile(r"\byou\s+are\s+now\b|\bagora\s+voc[êe]\s+é\b", re.IGNORECASE),
    # Marcadores de papel: "system:", [SYSTEM], <|system|>, ```system
    "marcador_system": re.compile(
        r"^\s*system\s*:|\[system\]|<\|system\|>|```\s*system", re.IGNORECASE | re.MULTILINE
    ),
    # Delimitadores de templates de prompt
    "delimitadores_prompt": re.compile(
        r"</?(?:system|assistant|user)>|\[INST\]|<<SYS>>|\[\[/INST\]\]", re.IGNORECASE
    ),
    # "releve/mostre o system prompt"
    "revelar_system_prompt": re.compile(
        r"(revel|mostr|exib|imprim|compartilh)[^\n.]{0,40}(system\s*prompt|prompt\s*de\s*sistema)",
        re.IGNORECASE,
    ),
}

# --- Camada 3: padrões adicionais verificados apenas na SAÍDA ---

PADROES_SAIDA: dict[str, re.Pattern[str]] = {
    # Resposta tentando alterar o comportamento do interlocutor
    "mudanca_comportamento": re.compile(
        r"a\s+partir\s+de\s+agora\s+(?:voc[êe]|voce|eu\s+devo|o\s+assistente|ignore)",
        re.IGNORECASE,
    ),
}

RESPOSTA_SEGURA_PADRAO = (
    "Desculpe, não posso fornecer esse conteúdo. Posso ajudar com dúvidas sobre "
    "normas, calendário acadêmico, notas, matrículas, boletos e outros serviços "
    "da universidade — é só perguntar."
)


def detect_injection(text: str) -> list[str]:
    """Detecta padrões de injeção no texto; retorna os nomes encontrados."""
    return [nome for nome, padrao in PADROES_INJECAO.items() if padrao.search(text)]


def separar_chunks_suspeitos(chunks: list) -> tuple[list, list]:
    """Divide chunks em (limpos, suspeitos) — camada de ingestão (T9.3)."""
    limpos, suspeitos = [], []
    for chunk in chunks:
        if detect_injection(chunk.text):
            suspeitos.append(chunk)
        else:
            limpos.append(chunk)
    return limpos, suspeitos


def _fragmentos_prompt_sistema() -> list[str]:
    """Trechos distintivos dos prompts de sistema (eco na resposta = vazamento)."""
    from src.agents.prompts.academico import ACADEMICO_SYSTEM_PROMPT
    from src.agents.prompts.documental import DOCUMENTAL_SYSTEM_PROMPT
    from src.agents.prompts.financeiro import FINANCEIRO_SYSTEM_PROMPT
    from src.agents.prompts.supervisor import SUPERVISOR_SYSTEM_PROMPT

    fragmentos = []
    for prompt in (
        SUPERVISOR_SYSTEM_PROMPT,
        ACADEMICO_SYSTEM_PROMPT,
        FINANCEIRO_SYSTEM_PROMPT,
        DOCUMENTAL_SYSTEM_PROMPT,
    ):
        primeira_linha = prompt.strip().splitlines()[0].strip()
        if len(primeira_linha) >= 20:
            fragmentos.append(primeira_linha)
    fragmentos.append("Responda APENAS com JSON válido, sem texto adicional")
    return fragmentos


FRAGMENTOS_PROMPT_SISTEMA = _fragmentos_prompt_sistema()


@dataclass
class GuardrailResult:
    """Resultado da validação de saída (T9.3)."""

    safe: bool
    reasons: list[str] = field(default_factory=list)


def validate_answer(answer: str) -> GuardrailResult:
    """Valida a resposta final antes de entregá-la ao usuário."""
    reasons: list[str] = []
    lower = answer.lower()

    for fragmento in FRAGMENTOS_PROMPT_SISTEMA:
        if fragmento.lower() in lower:
            reasons.append("eco_prompt_sistema")
            break

    if detect_injection(answer):
        reasons.append("eco_jailbreak")

    for nome, padrao in PADROES_SAIDA.items():
        if padrao.search(answer):
            reasons.append(nome)

    return GuardrailResult(safe=not reasons, reasons=reasons)


def registrar_guardrail_langsmith(run_id: uuid.UUID, reasons: list[str]) -> None:
    """Registra ``guardrail_triggered`` no LangSmith (melhor esforço)."""
    try:
        from langsmith import Client

        Client().create_feedback(
            run_id=run_id,
            key="guardrail_triggered",
            score=0.0,
            comment=", ".join(reasons),
        )
    except Exception:  # noqa: BLE001
        logger.debug("LangSmith indisponível; guardrail registrado apenas no log JSON.")


def log_guardrail(run_id: uuid.UUID, reasons: list[str], origem: str, **extra: object) -> None:
    """Evento estruturado ``guardrail_triggered`` no log JSON (T9.3)."""
    logger.warning(
        "Guardrail triggered",
        extra={
            "guardrail_triggered": True,
            "origem": origem,
            "reasons": reasons,
            "run_id": str(run_id),
            **extra,
        },
    )
