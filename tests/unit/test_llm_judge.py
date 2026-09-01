"""Testes unitários do avaliador semântico estruturado LLM-as-a-Judge."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from src.evaluation.llm_judge import (
    LLMJudge,
    avaliar_heuristicamente,
    build_judge_prompt,
    parse_judgment_response,
)


def test_build_judge_prompt_contem_campos_essenciais() -> None:
    prompt = build_judge_prompt(
        question="Quando começa o semestre?",
        answer="O semestre letivo começa em 15/03/2026.",
        reference_answer="O calendário define o início em 15/03/2026.",
        category="direct",
        contexts=["Calendário acadêmico 2026.2"],
    )
    assert "Quando começa o semestre?" in prompt
    assert "15/03/2026" in prompt
    assert "faithfulness" in prompt
    assert "answer_relevancy" in prompt
    assert "---BEGIN EVALUATION DATA---" in prompt


def test_parse_judgment_response_valido() -> None:
    raw = json.dumps(
        {
            "faithfulness": 0.95,
            "context_precision": 0.90,
            "context_recall": 0.85,
            "answer_relevancy": 1.0,
            "rationale": "A resposta está excelente e fundamentada nos documentos.",
        }
    )
    scores, rationale = parse_judgment_response(raw)
    assert scores["faithfulness"] == 0.95
    assert scores["context_precision"] == 0.90
    assert scores["context_recall"] == 0.85
    assert scores["answer_relevancy"] == 1.0
    assert "excelente" in rationale


def test_parse_judgment_response_com_markdown_block() -> None:
    raw = """```json
{
  "faithfulness": 1.0,
  "context_precision": 0.8,
  "context_recall": 0.9,
  "answer_relevancy": 0.85,
  "rationale": "Markdown envelopado corretamente."
}
```"""
    scores, rationale = parse_judgment_response(raw)
    assert scores["faithfulness"] == 1.0
    assert "Markdown" in rationale


def test_parse_judgment_response_clamp_valores() -> None:
    raw = json.dumps(
        {
            "faithfulness": 1.5,
            "context_precision": -0.2,
            "context_recall": 0.8,
            "answer_relevancy": 1.0,
            "rationale": "Valores fora do range normalizados.",
        }
    )
    scores, _ = parse_judgment_response(raw)
    assert scores["faithfulness"] == 1.0
    assert scores["context_precision"] == 0.0


def test_parse_judgment_response_invalido_lanca_erro() -> None:
    with pytest.raises(ValueError, match="JSON"):
        parse_judgment_response("não é json")

    with pytest.raises(ValueError, match="Métrica"):
        parse_judgment_response(json.dumps({"faithfulness": "invalido", "rationale": "ok"}))


def test_avaliar_heuristicamente_fora_de_escopo() -> None:
    pergunta = {"category": "fora_de_escopo", "reference_answer": "fora do escopo"}
    res = avaliar_heuristicamente(pergunta, "Essa pergunta está fora do escopo institucional.")
    assert res["faithfulness"] == 1.0
    assert res["answer_relevancy"] == 1.0


def test_avaliar_heuristicamente_sem_resposta() -> None:
    pergunta = {"category": "sem_resposta", "reference_answer": "não encontrei"}
    res_honesto = avaliar_heuristicamente(
        pergunta, "Não encontrei essa informação nos documentos oficiais."
    )
    assert res_honesto["faithfulness"] == 1.0

    res_inventado = avaliar_heuristicamente(pergunta, "O valor é de R$ 500,00 e precisa de senha.")
    assert res_inventado["faithfulness"] == 0.0


def test_llm_judge_invoke_com_mock() -> None:
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(
        content=json.dumps(
            {
                "faithfulness": 0.92,
                "context_precision": 0.88,
                "context_recall": 0.85,
                "answer_relevancy": 0.95,
                "rationale": "Resposta correta e bem fundamentada.",
            }
        )
    )

    judge = LLMJudge(chat_model=mock_model)
    assert judge.is_available is True

    pergunta = {
        "question": "Como solicitar licença capacitação?",
        "reference_answer": "O Guia do Servidor define o procedimento de licença capacitação.",
        "category": "direct",
    }
    resultado = judge.evaluate(pergunta, "A licença capacitação é solicitada via SIGRH.")

    assert resultado["faithfulness"] == 0.92
    assert resultado["answer_relevancy"] == 0.95
    assert "correta" in resultado["rationale"]


@pytest.mark.asyncio
async def test_llm_judge_ainvoke_com_fallback_em_erro() -> None:
    mock_model = MagicMock()
    mock_model.ainvoke.side_effect = RuntimeError("Erro de conexão de teste")

    judge = LLMJudge(chat_model=mock_model, fallback_to_heuristic=True)
    pergunta = {
        "question": "Onde fica o restaurante universitário?",
        "reference_answer": "Essa pergunta está fora do escopo da plataforma UsiEdu.",
        "category": "fora_de_escopo",
    }
    resultado = await judge.aevaluate(pergunta, "Essa dúvida está fora do escopo.")

    assert resultado["faithfulness"] == 1.0
    assert "[Fallback Heurístico]" in resultado["rationale"]
