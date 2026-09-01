"""Avaliador semântico estruturado (LLM-as-a-Judge) por rubricas para o UsiEdu.

Implementa avaliação de qualidade RAG conforme RF-29 e protocolo rubric-judge-v1:
- faithfulness: fidelidade aos contextos recuperados (sem alucinação)
- context_precision: proporção de trechos recuperados relevantes
- context_recall: cobertura dos fatos necessários pela recuperação
- answer_relevancy: pertinência direta e completude da resposta
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

logger = logging.getLogger("usiedu.evaluation.judge")

METRIC_NAMES = (
    "faithfulness",
    "context_precision",
    "context_recall",
    "answer_relevancy",
)

JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def _is_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def build_judge_prompt(
    question: str,
    answer: str,
    reference_answer: str,
    category: str,
    contexts: list[str] | None = None,
) -> str:
    """Monta o prompt para o modelo juiz com rubricas claras."""
    item = {
        "question": question,
        "answer": answer,
        "reference_answer": reference_answer,
        "category": category,
        "contexts": contexts or [],
    }
    payload = json.dumps(item, ensure_ascii=False, indent=2)
    return f"""## Role
Você é um juiz avaliador independente e imparcial de qualidade de sistemas RAG.

## Task
Avalie a resposta fornecida em quatro dimensões métricas, com valores entre 0.0 e 1.0:
- faithfulness: Afirmações sustentadas pelos contextos/referência, sem inventar fatos.
- context_precision: Trechos recuperados úteis e focados para responder (1.0 se s/ busca).
- context_recall: Cobertura dos fatos essenciais exigidos pela referência (1.0 se s/ busca).
- answer_relevancy: Resposta direta, clara e pertinente à dúvida, sem evasivas.

## Regras Especiais
1. Se category for "fora_de_escopo", a resposta deve redirecionar ou informar o escopo.
2. Se category for "sem_resposta", a resposta deve admitir que a informação não foi encontrada.
3. Se category for "direct", a resposta deve ser precisa e embasada.

## Output Format
Retorne estritamente um objeto JSON válido (sem tags markdown adicionais) no formato:
{{
  "faithfulness": 0.0,
  "context_precision": 0.0,
  "context_recall": 0.0,
  "answer_relevancy": 0.0,
  "rationale": "Justificativa curta e objetiva em português."
}}

## Input Data
---BEGIN EVALUATION DATA---
{payload}
---END EVALUATION DATA---"""


def parse_judgment_response(content: str) -> tuple[dict[str, float], str]:
    """Faz o parse seguro do JSON retornado pelo juiz."""
    raw = content.strip()
    match = JSON_BLOCK_PATTERN.search(raw)
    if match:
        raw = match.group(1)

    try:
        parsed = json.loads(raw)
    except Exception as exc:
        msg = f"Falha ao decodificar JSON do juiz: {exc}. Raw: {raw[:200]}"
        raise ValueError(msg) from exc

    if not isinstance(parsed, dict):
        raise ValueError("Saída do juiz não é um dicionário JSON")

    rationale = parsed.get("rationale", "")
    if not isinstance(rationale, str):
        rationale = str(rationale)

    scores: dict[str, float] = {}
    for metric in METRIC_NAMES:
        val = parsed.get(metric)
        if not _is_number(val):
            raise ValueError(f"Métrica '{metric}' ausente ou não numérica no julgamento")
        scores[metric] = max(0.0, min(1.0, float(val)))

    return scores, rationale


def avaliar_heuristicamente(
    pergunta: dict[str, Any],
    resposta: str,
) -> dict[str, Any]:
    """Fallback determinístico de avaliação por heurística de palavras-chave."""
    ref = pergunta.get("reference_answer", "").lower()
    resp = resposta.lower()
    cat = pergunta.get("category", "direct")

    palavras = [p for p in ref.split() if len(p) > 4]
    if not palavras:
        return {
            "faithfulness": 1.0,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "answer_relevancy": 1.0,
            "rationale": "Heurística: sem palavras-chave mínimas na referência.",
        }

    cobertas = sum(1 for p in palavras if p in resp)
    cobertura = cobertas / len(palavras)

    if cat == "fora_de_escopo":
        negacao = any(
            t in resp
            for t in [
                "fora do escopo",
                "não encontrei",
                "fora de escopo",
                "não posso",
                "fora do meu escopo",
            ]
        )
        score = 1.0 if negacao else 0.0
        return {
            "faithfulness": score,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "answer_relevancy": score,
            "rationale": "Heurística: verificação de negação/redirecionamento fora de escopo.",
        }

    if cat == "sem_resposta":
        honesto = any(
            t in resp
            for t in [
                "não encontrei",
                "não sei",
                "não encontrada",
                "não disponível",
                "não localizei",
            ]
        )
        score = 1.0 if honesto else 0.0
        return {
            "faithfulness": score,
            "context_precision": 1.0,
            "context_recall": 1.0,
            "answer_relevancy": score,
            "rationale": "Heurística: verificação de recusa honesta.",
        }

    return {
        "faithfulness": min(cobertura + 0.3, 1.0),
        "context_precision": min(cobertura + 0.2, 1.0),
        "context_recall": min(cobertura + 0.2, 1.0),
        "answer_relevancy": min(cobertura + 0.3, 1.0),
        "rationale": f"Heurística de cobertura de termos ({cobertas}/{len(palavras)}).",
    }


class LLMJudge:
    """Juiz semântico para avaliação de respostas RAG."""

    def __init__(
        self,
        chat_model: BaseChatModel | None = None,
        model_name: str | None = None,
        temperature: float | None = None,
        fallback_to_heuristic: bool = True,
    ) -> None:
        self.fallback_to_heuristic = fallback_to_heuristic
        self._model = chat_model

        if self._model is None and os.getenv("OPENCODE_GO_API_KEY"):
            try:
                from src.llm.provider import get_chat_model

                self._model = get_chat_model(
                    model_name=model_name or os.getenv("USIEDU_JUDGE_MODEL", "deepseek-v4-flash"),
                    temperature=temperature,
                    max_tokens=2048,
                )
            except Exception as exc:
                logger.warning("Não foi possível instanciar modelo juiz LLM: %s", exc)
                self._model = None

    @property
    def is_available(self) -> bool:
        """Indica se o modelo juiz LLM está configurado e disponível."""
        return self._model is not None

    def evaluate(
        self,
        pergunta: dict[str, Any],
        resposta: str,
        contextos: list[str] | None = None,
    ) -> dict[str, Any]:
        """Avalia síncronamente a resposta do assistente."""
        if not self.is_available:
            return avaliar_heuristicamente(pergunta, resposta)

        prompt_text = build_judge_prompt(
            question=pergunta.get("question", ""),
            answer=resposta,
            reference_answer=pergunta.get("reference_answer", ""),
            category=pergunta.get("category", "direct"),
            contexts=contextos or [],
        )

        try:
            response = self._model.invoke([HumanMessage(content=prompt_text)])
            content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            scores, rationale = parse_judgment_response(content)
            scores["rationale"] = rationale
            return scores
        except Exception as exc:
            logger.warning("Falha no julgamento LLM (%s), acionando fallback", exc)
            if self.fallback_to_heuristic:
                res = avaliar_heuristicamente(pergunta, resposta)
                res["rationale"] = f"[Fallback Heurístico] {res.get('rationale', '')}"
                return res
            raise

    async def aevaluate(
        self,
        pergunta: dict[str, Any],
        resposta: str,
        contextos: list[str] | None = None,
    ) -> dict[str, Any]:
        """Avalia assincronamente a resposta do assistente."""
        if not self.is_available:
            return avaliar_heuristicamente(pergunta, resposta)

        prompt_text = build_judge_prompt(
            question=pergunta.get("question", ""),
            answer=resposta,
            reference_answer=pergunta.get("reference_answer", ""),
            category=pergunta.get("category", "direct"),
            contexts=contextos or [],
        )

        try:
            response = await self._model.ainvoke([HumanMessage(content=prompt_text)])
            content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            scores, rationale = parse_judgment_response(content)
            scores["rationale"] = rationale
            return scores
        except Exception as exc:
            logger.warning("Falha no julgamento LLM assíncrono (%s), acionando fallback", exc)
            if self.fallback_to_heuristic:
                res = avaliar_heuristicamente(pergunta, resposta)
                res["rationale"] = f"[Fallback Heurístico] {res.get('rationale', '')}"
                return res
            raise
