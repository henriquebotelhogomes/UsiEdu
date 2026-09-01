"""Testes do módulo de Query Rewriting e Resolução Coreferencial para RAG."""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.rag.query_rewriter import _format_recent_history, rewrite_query_for_rag


class MockRewriterLLM:
    """Mock assíncrono de LLM para testar reescrita de consulta."""

    def __init__(self, response_text: str = "Qual o prazo de trancamento de matrícula?") -> None:
        self.response_text = response_text
        self.call_count = 0

    async def ainvoke(self, messages: list) -> AIMessage:
        self.call_count += 1
        return AIMessage(content=self.response_text)


class ErrorRewriterLLM:
    """Mock de LLM que simula falha/exceção."""

    async def ainvoke(self, messages: list) -> AIMessage:
        raise RuntimeError("Erro simulado na chamada do LLM")


class TestQueryRewriter:
    """Testes unitários para rewrite_query_for_rag."""

    @pytest.mark.asyncio
    async def test_mensagens_vazias_retorna_string_vazia(self) -> None:
        """Lista vazia de mensagens deve retornar string vazia."""
        res = await rewrite_query_for_rag([])
        assert res == ""

    @pytest.mark.asyncio
    async def test_primeiro_turno_executa_fast_path_sem_chamar_llm(self) -> None:
        """Quando há apenas 1 mensagem, deve retornar a query original sem chamar o LLM."""
        llm = MockRewriterLLM()
        messages = [HumanMessage(content="Como funciona o trancamento de matrícula?")]

        res = await rewrite_query_for_rag(messages, llm=llm)
        assert res == "Como funciona o trancamento de matrícula?"
        assert llm.call_count == 0  # Zero Latency Fast-path

    @pytest.mark.asyncio
    async def test_multi_turno_sem_llm_retorna_query_original(self) -> None:
        """Multi-turno sem LLM configurado deve retornar a query original de forma segura."""
        messages = [
            HumanMessage(content="Como funciona o trancamento?"),
            AIMessage(content="O trancamento pode ser total ou parcial..."),
            HumanMessage(content="Qual a data limite dele?"),
        ]

        res = await rewrite_query_for_rag(messages, llm=None)
        assert res == "Qual a data limite dele?"

    @pytest.mark.asyncio
    async def test_multi_turno_reescreve_pronomes_com_llm(self) -> None:
        """Multi-turno com pronomes deve chamar LLM e retornar a consulta reescrita."""
        llm = MockRewriterLLM(
            response_text="Qual a data limite para trancamento de matrícula no semestre 2026.2?"
        )
        messages = [
            HumanMessage(content="Como funciona o trancamento de matrícula?"),
            AIMessage(content="O trancamento encerra as atividades no semestre vigente."),
            HumanMessage(content="Qual a data limite dele no semestre 2026.2?"),
        ]

        res = await rewrite_query_for_rag(messages, llm=llm)
        assert res == "Qual a data limite para trancamento de matrícula no semestre 2026.2?"
        assert llm.call_count == 1

    @pytest.mark.asyncio
    async def test_fallback_gracioso_em_caso_de_erro_no_llm(self) -> None:
        """Se o LLM falhar, a função deve capturar o erro e retornar a query original."""
        llm = ErrorRewriterLLM()
        messages = [
            HumanMessage(content="Quero saber sobre o regimento."),
            AIMessage(content="O regimento define as regras gerais."),
            HumanMessage(content="E o artigo 15 dele?"),
        ]

        res = await rewrite_query_for_rag(messages, llm=llm)
        assert res == "E o artigo 15 dele?"

    def test_format_recent_history(self) -> None:
        """_format_recent_history deve formatar o histórico recente excluindo a última query."""
        messages = [
            HumanMessage(content="Pergunta 1"),
            AIMessage(content="Resposta 1"),
            HumanMessage(content="Pergunta 2"),
        ]
        history = _format_recent_history(messages)
        assert "Usuário: Pergunta 1" in history
        assert "Assistente: Resposta 1" in history
        assert "Pergunta 2" not in history


class TestExtractQueryMetadata:
    """Testes unitários para extract_query_metadata (Self-Querying)."""

    def test_extract_query_metadata_regimento(self) -> None:
        from src.rag.query_rewriter import extract_query_metadata

        meta = extract_query_metadata("O que diz o Regimento Geral sobre faltas?")
        assert meta.get("documento") == "Regimento Geral da UnB"

    def test_extract_query_metadata_calendario(self) -> None:
        from src.rag.query_rewriter import extract_query_metadata

        meta = extract_query_metadata("Quando começa o semestre no calendário acadêmico?")
        assert meta.get("documento") == "Calendário Acadêmico 2026.2"

    def test_extract_query_metadata_sem_documento(self) -> None:
        from src.rag.query_rewriter import extract_query_metadata

        meta = extract_query_metadata("Como tirar segunda via de carteirinha?")
        assert meta == {}
