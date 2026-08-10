"""Guardrails contra prompt injection (T9.3).

Três camadas de defesa, todas com heurísticas determinísticas (regex) e
**testáveis sem LLM**:

1. **Ingestão:** cada chunk passa por :func:`detect_injection`; chunks
   sinalizados ganham ``suspicious=true`` e são **excluídos do índice**
   com log de auditoria (integrado em ``src/rag/ingest.py``).
2. **Entrada do usuário:** o mesmo detector roda na pergunta; se sinalizada,
   o trace recebe ``flagged=true`` — a pergunta NÃO é bloqueada (risco de
   falso positivo), apenas observada.
3. **Saída:** :func:`validate_answer` verifica se a resposta final ecoa o
   prompt de sistema, ecoa instruções de jailbreak ou tenta alterar o
   comportamento do usuário ("a partir de agora..."). Se insegura, é
   substituída por :data:`RESPOSTA_SEGURA_PADRAO` e o evento
   ``guardrail_triggered`` é registrado (log JSON + LangSmith best-effort).
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

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
    """Divide chunks em (limpos, suspeitos) — camada de ingestão (T9.3).

    Chunks suspeitos devem receber ``metadata["suspicious"] = True`` e ser
    excluídos do índice, com log de auditoria no chamador.
    """
    limpos, suspeitos = [], []
    for chunk in chunks:
        if detect_injection(chunk.text):
            suspeitos.append(chunk)
        else:
            limpos.append(chunk)
    return limpos, suspeitos


def _fragmentos_prompt_sistema() -> list[str]:
    """Trechos distintivos dos prompts de sistema (eco na resposta = vazamento).

    Derivados dos prompts reais na importação para não dessincronizar.
    """
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
    """Valida a resposta final antes de entregá-la ao usuário.

    Insegura quando: ecoa trecho do prompt de sistema, ecoa instruções de
    injeção/jailbreak, ou tenta alterar o comportamento ("a partir de
    agora..."). Nunca bloqueia respostas limpas.
    """
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
    """Registra ``guardrail_triggered`` no LangSmith (melhor esforço).

    Espelha o padrão de ``feedback.py``: falha do LangSmith nunca afeta a
    resposta ao usuário — o log JSON já contém o evento.
    """
    try:
        from langsmith import Client

        Client().create_feedback(
            run_id=run_id,
            key="guardrail_triggered",
            score=0.0,
            comment=", ".join(reasons),
        )
    except Exception:  # noqa: BLE001 — LangSmith é observabilidade, não bloqueio
        logger.debug("LangSmith indisponível; guardrail registrado apenas no log JSON.")


def log_guardrail(run_id: uuid.UUID, reasons: list[str], origem: str, **extra) -> None:
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
