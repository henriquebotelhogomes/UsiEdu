"""Testes do dataset de avaliação e do script Ragas."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.run_ragas import carregar_dataset

DATASET_PATH = Path(__file__).parent.parent.parent / "src" / "evaluation" / "dataset.jsonl"


class TestDataset:
    """Testes do dataset de avaliação (RF-28)."""

    def test_dataset_existe(self) -> None:
        """Dataset deve existir no caminho esperado."""
        assert DATASET_PATH.exists()

    def test_dataset_tem_30_perguntas(self) -> None:
        """Dataset deve ter exatamente 30 perguntas."""
        perguntas = carregar_dataset(DATASET_PATH)
        assert len(perguntas) == 30

    def test_dataset_15_student_15_staff(self) -> None:
        """Dataset deve ter 15 perguntas por perfil."""
        perguntas = carregar_dataset(DATASET_PATH)
        students = [p for p in perguntas if p["profile"] == "student"]
        staff = [p for p in perguntas if p["profile"] == "staff"]
        assert len(students) == 15
        assert len(staff) == 15

    def test_dataset_ids_unicos(self) -> None:
        """IDs das perguntas devem ser únicos."""
        perguntas = carregar_dataset(DATASET_PATH)
        ids = [p["id"] for p in perguntas]
        assert len(ids) == len(set(ids))

    def test_dataset_campos_obrigatorios(self) -> None:
        """Toda pergunta deve ter os campos obrigatórios."""
        perguntas = carregar_dataset(DATASET_PATH)
        for p in perguntas:
            assert p["id"]
            assert p["profile"] in ("student", "staff")
            assert p["user_id"]
            assert p["question"]
            assert p["reference_answer"]
            assert p["category"] in (
                "direct",
                "tool",
                "composta",
                "fora_de_escopo",
                "sem_resposta",
            )

    def test_dataset_tem_todas_categorias(self) -> None:
        """Dataset deve cobrir todas as categorias do RF-28."""
        perguntas = carregar_dataset(DATASET_PATH)
        categorias = {p["category"] for p in perguntas}
        assert {"direct", "tool", "composta", "fora_de_escopo", "sem_resposta"} <= categorias

    def test_dataset_json_valido(self) -> None:
        """Cada linha do dataset deve ser JSON válido."""
        with DATASET_PATH.open(encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if linha:
                    assert json.loads(linha)  # não deve levantar exceção


class TestRunRagas:
    """Testes do script de avaliação."""

    def test_carregar_dataset_retorna_lista(self) -> None:
        """carregar_dataset deve retornar lista de dicts."""
        perguntas = carregar_dataset(DATASET_PATH)
        assert isinstance(perguntas, list)
        assert all(isinstance(p, dict) for p in perguntas)

    def test_avaliar_resposta_direct(self) -> None:
        """Resposta com palavras-chave da referência deve pontuar bem."""
        from src.evaluation.run_ragas import _avaliar_resposta

        pergunta = {
            "reference_answer": (
                "O trancamento de matrícula está previsto no Regimento Geral da UnB"
            ),
            "category": "direct",
        }
        metricas = _avaliar_resposta(
            pergunta, "O trancamento de matrícula está previsto no Regimento Geral da UnB"
        )
        assert metricas["faithfulness"] > 0.5

    def test_avaliar_resposta_fora_escopo(self) -> None:
        """Resposta que nega/redireciona deve pontuar bem em fora_de_escopo."""
        from src.evaluation.run_ragas import _avaliar_resposta

        pergunta = {"reference_answer": "fora do escopo", "category": "fora_de_escopo"}
        metricas = _avaliar_resposta(pergunta, "Essa pergunta está fora do escopo da plataforma.")
        assert metricas["faithfulness"] == 1.0

    def test_avaliar_resposta_sem_resposta_honesta(self) -> None:
        """Resposta honesta ('não encontrei') deve pontuar bem em sem_resposta."""
        from src.evaluation.run_ragas import _avaliar_resposta

        pergunta = {"reference_answer": "não encontrei", "category": "sem_resposta"}
        metricas = _avaliar_resposta(
            pergunta, "Não encontrei essa informação nos documentos oficiais."
        )
        assert metricas["faithfulness"] == 1.0

    def test_avaliar_resposta_sem_resposta_desonesta(self) -> None:
        """Resposta que inventa deve pontuar mal em sem_resposta."""
        from src.evaluation.run_ragas import _avaliar_resposta

        pergunta = {"reference_answer": "não encontrei", "category": "sem_resposta"}
        metricas = _avaliar_resposta(pergunta, "O procedimento exige 3 documentos e taxa de R$ 50.")
        assert metricas["faithfulness"] == 0.0

    def test_formatar_metricas_media(self) -> None:
        """_formatar_metricas deve calcular médias corretamente."""
        from src.evaluation.run_ragas import _formatar_metricas

        metricas = [
            {
                "faithfulness": 1.0,
                "context_precision": 0.5,
                "context_recall": 0.5,
                "answer_relevancy": 1.0,
            },
            {
                "faithfulness": 0.5,
                "context_precision": 0.5,
                "context_recall": 0.5,
                "answer_relevancy": 0.5,
            },
        ]
        medias = _formatar_metricas(metricas)
        assert medias["faithfulness"] == 0.75
        assert medias["context_precision"] == 0.5
        assert medias["answer_relevancy"] == 0.75

    def test_formatar_metricas_vazio(self) -> None:
        """_formatar_metricas com lista vazia deve retornar zeros."""
        from src.evaluation.run_ragas import _formatar_metricas

        medias = _formatar_metricas([])
        assert medias["faithfulness"] == 0.0
        assert medias["answer_relevancy"] == 0.0

    def test_extrair_resposta(self) -> None:
        """_extrair_resposta deve extrair a última mensagem."""
        from langchain_core.messages import AIMessage, HumanMessage

        from src.evaluation.run_ragas import _extrair_resposta

        result = {
            "messages": [HumanMessage(content="pergunta"), AIMessage(content="resposta final")]
        }
        assert _extrair_resposta(result) == "resposta final"

    def test_extrair_resposta_vazia(self) -> None:
        """_extrair_resposta sem mensagens deve retornar string vazia."""
        from src.evaluation.run_ragas import _extrair_resposta

        assert _extrair_resposta({}) == ""

    def test_extrair_contexto_dict(self) -> None:
        """_extrair_contexto deve lidar com sources como dict."""
        from src.evaluation.run_ragas import _extrair_contexto

        result = {"retrieved_sources": [{"excerpt": "trecho 1"}, {"excerpt": "trecho 2"}]}
        assert _extrair_contexto(result) == ["trecho 1", "trecho 2"]

    def test_extrair_contexto_vazio(self) -> None:
        """_extrair_contexto sem fontes deve retornar lista vazia."""
        from src.evaluation.run_ragas import _extrair_contexto

        assert _extrair_contexto({}) == []

    def test_gerar_relatorio_cria_arquivo(self, tmp_path) -> None:
        """_gerar_relatorio deve criar o arquivo Markdown."""
        from src.evaluation.run_ragas import _gerar_relatorio

        perguntas = [
            {
                "id": "q001",
                "profile": "student",
                "category": "direct",
                "question": "Pergunta de teste?",
            }
        ]
        resultados = [{"faithfulness": 0.9, "answer_relevancy": 0.9}]
        medias = {
            "faithfulness": 0.9,
            "context_precision": 0.8,
            "context_recall": 0.8,
            "answer_relevancy": 0.9,
        }
        output = tmp_path / "relatorio.md"

        _gerar_relatorio(perguntas, resultados, medias, output, "teste")
        assert output.exists()
        conteudo = output.read_text(encoding="utf-8")
        assert "# Relatório de Avaliação Ragas — UsiEdu" in conteudo
        assert "q001" in conteudo
        assert "✅" in conteudo

    def test_gerar_relatorio_metas_nao_atingidas(self, tmp_path) -> None:
        """_gerar_relatorio deve marcar ❌ quando metas não atingidas."""
        from src.evaluation.run_ragas import _gerar_relatorio

        perguntas = [{"id": "q001", "profile": "student", "category": "direct", "question": "P"}]
        resultados = [{"faithfulness": 0.1, "answer_relevancy": 0.1}]
        medias = {
            "faithfulness": 0.1,
            "context_precision": 0.1,
            "context_recall": 0.1,
            "answer_relevancy": 0.1,
        }
        output = tmp_path / "relatorio_falha.md"

        _gerar_relatorio(perguntas, resultados, medias, output, "teste")
        conteudo = output.read_text(encoding="utf-8")
        assert "❌" in conteudo

    @pytest.mark.asyncio
    async def test_executar_avaliacao_gera_relatorio(self, tmp_path, monkeypatch) -> None:
        """executar_avaliacao deve gerar relatório para o dataset (limit 2)."""
        from src.evaluation.run_ragas import executar_avaliacao

        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
        output = tmp_path / "relatorio_eval.md"
        resultado = await executar_avaliacao(dataset_path=DATASET_PATH, output_path=output, limit=2)
        assert resultado == output
        assert output.exists()

    def test_main_executa_cli(self, tmp_path, monkeypatch) -> None:
        """main deve executar a CLI com sucesso."""
        from src.evaluation.run_ragas import main

        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_ragas",
                "--dataset",
                str(DATASET_PATH),
                "--output",
                str(tmp_path / "r.md"),
                "--limit",
                "1",
            ],
        )
        main()
        assert (tmp_path / "r.md").exists()


class TestFeedbackNegativo:
    """Testes da integração do feedback negativo no relatório (T8.1)."""

    def test_similaridade_jaccard(self) -> None:
        """Jaccard: idênticas → 1.0, disjuntas → 0.0, parciais entre 0 e 1."""
        from src.evaluation.run_ragas import _similaridade_jaccard

        assert _similaridade_jaccard("a b c", "A B C") == 1.0
        assert _similaridade_jaccard("a b", "c d") == 0.0
        assert _similaridade_jaccard("", "") == 1.0
        assert _similaridade_jaccard("a", "") == 0.0
        assert _similaridade_jaccard("a b", "a c") == pytest.approx(1 / 3)

    def test_secao_feedback_vazia(self) -> None:
        """Sem casos exportados, a seção orienta rodar o script de exportação."""
        from src.evaluation.run_ragas import _gerar_secao_feedback

        linhas = _gerar_secao_feedback([], pulados=0)
        texto = "\n".join(linhas)
        assert "## Casos de feedback negativo (T8.1)" in texto
        assert "export_feedback_to_eval.py" in texto

    def test_secao_feedback_com_casos(self) -> None:
        """Casos avaliados devem aparecer em tabela com status e pulados."""
        from src.evaluation.run_ragas import _gerar_secao_feedback

        resultados = [
            {
                "message_id": "abcdef12-0000-0000-0000-000000000000",
                "question": "Quando começa o semestre?",
                "user_comment": "resposta errada",
                "similaridade": 0.20,
                "status": "🔄 Alterada — revisão manual",
            },
            {
                "message_id": "fedcba98-0000-0000-0000-000000000000",
                "question": "Quais os requisitos?",
                "user_comment": None,
                "similaridade": 0.98,
                "status": "❌ Repete resposta rejeitada",
            },
        ]
        texto = "\n".join(_gerar_secao_feedback(resultados, pulados=1))
        assert "2 caso(s) reavaliado(s), 1 pulado(s)" in texto
        assert "abcdef12" in texto
        assert "❌ Repete resposta rejeitada" in texto
        assert "0.20" in texto

    @pytest.mark.asyncio
    async def test_executar_avaliacao_com_feedback(self, tmp_path, monkeypatch) -> None:
        """executar_avaliacao deve reavaliar casos do JSONL e renderizar a seção."""
        from src.evaluation.run_ragas import executar_avaliacao

        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)  # modo offline/fake

        feedback_path = tmp_path / "feedback_negativo.jsonl"
        caso = {
            "question": "Quando começa o semestre letivo 2026.2?",
            "rejected_answer": "Resposta antiga rejeitada pelo usuário.",
            "user_comment": "não respondeu",
            "profile": "student",
            "session_id": "s1",
            "message_id": "abcdef12-0000-0000-0000-000000000000",
            "created_at": "2026-08-01T10:00:00",
        }
        feedback_path.write_text(json.dumps(caso, ensure_ascii=False) + "\n", encoding="utf-8")

        output = tmp_path / "relatorio_fb.md"
        await executar_avaliacao(
            dataset_path=DATASET_PATH,
            output_path=output,
            limit=1,
            feedback_path=feedback_path,
        )
        conteudo = output.read_text(encoding="utf-8")
        assert "## Casos de feedback negativo (T8.1)" in conteudo
        assert "abcdef12" in conteudo

    @pytest.mark.asyncio
    async def test_executar_avaliacao_pula_sem_pergunta(self, tmp_path, monkeypatch) -> None:
        """Casos com question: null devem ser contabilizados como pulados."""
        from src.evaluation.run_ragas import executar_avaliacao

        monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)  # modo offline/fake

        feedback_path = tmp_path / "feedback_negativo.jsonl"
        caso = {
            "question": None,
            "rejected_answer": None,
            "user_comment": None,
            "profile": "student",
            "session_id": "s1",
            "message_id": "sem-pergunta",
            "created_at": "2026-08-01T10:00:00",
        }
        feedback_path.write_text(json.dumps(caso, ensure_ascii=False) + "\n", encoding="utf-8")

        output = tmp_path / "relatorio_pulo.md"
        await executar_avaliacao(
            dataset_path=DATASET_PATH,
            output_path=output,
            limit=1,
            feedback_path=feedback_path,
        )
        conteudo = output.read_text(encoding="utf-8")
        assert "1 pulado(s) sem pergunta" in conteudo


class TestHeuristicasAmpliadas:
    """Testes das frases adicionadas às heurísticas de recusa."""

    def test_fora_escopo_resposta_padrao_do_no(self) -> None:
        """A resposta padrão do nó ('fora do meu escopo') deve pontuar 1.0."""
        from src.evaluation.run_ragas import _avaliar_resposta

        pergunta = {"reference_answer": "fora do escopo", "category": "fora_de_escopo"}
        resposta = (
            "Sou o assistente da UsiEdu e atendo dúvidas acadêmicas, financeiras e "
            "institucionais. Esse assunto está fora do meu escopo, mas posso ajudar "
            "com algum desses temas?"
        )
        metricas = _avaliar_resposta(pergunta, resposta)
        assert metricas["faithfulness"] == 1.0
        assert metricas["answer_relevancy"] == 1.0

    def test_sem_resposta_nao_localizei(self) -> None:
        """Recusa honesta com 'não localizei' deve pontuar 1.0 em sem_resposta."""
        from src.evaluation.run_ragas import _avaliar_resposta

        pergunta = {"reference_answer": "não encontrei", "category": "sem_resposta"}
        metricas = _avaliar_resposta(
            pergunta, "Não localizei informações oficiais sobre esse tema nos documentos."
        )
        assert metricas["faithfulness"] == 1.0


class TestCIGate:
    """Testes da validação real do CI Quality Gate (RF4-04)."""

    RELATORIO_BASE = (
        "# Relatório de Avaliação Ragas — UsiEdu\n\n"
        "| Métrica | Meta | Resultado | Status |\n"
        "|---|---|---|---|\n"
        "| faithfulness | ≥ 0.9 | {f} | {sf} |\n"
        "| context_precision | ≥ 0.8 | {cp} | {scp} |\n"
        "| context_recall | ≥ 0.8 | {cr} | {scr} |\n"
        "| answer_relevancy | ≥ 0.85 | {ar} | {sar} |\n"
    )

    def _escrever(self, tmp_path, f, cp, cr, ar) -> Path:
        conteudo = self.RELATORIO_BASE.format(
            f=f, sf="✅", cp=cp, scp="✅", cr=cr, scr="✅", ar=ar, sar="✅"
        )
        path = tmp_path / "relatorio_gate.md"
        path.write_text(conteudo, encoding="utf-8")
        return path

    def test_gate_aprova_quando_todas_acima(self, tmp_path) -> None:
        """Gate deve aprovar quando todas as métricas >= threshold."""
        from src.evaluation.run_ragas import _verificar_gate

        path = self._escrever(tmp_path, "0.91", "0.85", "0.85", "0.90")
        aprovado, valores = _verificar_gate(path, 0.80)
        assert aprovado is True
        assert valores["faithfulness"] == pytest.approx(0.91)

    def test_gate_reprova_quando_abaixo(self, tmp_path) -> None:
        """Gate deve reprovar quando alguma métrica < threshold."""
        from src.evaluation.run_ragas import _verificar_gate

        path = self._escrever(tmp_path, "0.65", "0.85", "0.85", "0.90")
        aprovado, valores = _verificar_gate(path, 0.80)
        assert aprovado is False
        assert valores["faithfulness"] == pytest.approx(0.65)

    def test_gate_reprova_relatorio_sem_metricas(self, tmp_path) -> None:
        """Relatório sem tabela de métricas deve reprovar o gate."""
        from src.evaluation.run_ragas import _verificar_gate

        path = tmp_path / "vazio.md"
        path.write_text("# Relatório sem métricas\n", encoding="utf-8")
        aprovado, valores = _verificar_gate(path, 0.80)
        assert aprovado is False
        assert valores == {}


class TestInstrumentoDeAvaliacao:
    """A avaliação mede a stack de produção e nunca confunde falha de execução com resposta ruim."""

    def _stub_llm(self, monkeypatch):
        """Substitui provider/Qdrant/RAG/grafos e registra o que foi construído."""
        from types import SimpleNamespace
        from unittest.mock import MagicMock

        import qdrant_client

        import src.llm.provider as provider
        import src.orchestration.graph as graph_mod
        import src.rag.embedder as embedder_mod
        import src.rag.reranker as reranker_mod
        import src.rag.retriever as retriever_mod

        monkeypatch.setenv("OPENCODE_GO_API_KEY", "chave-de-teste")
        llm: list[dict] = []
        retrievers: list[dict] = []
        mocks: list[MagicMock] = []
        graph_kwargs: dict = {}

        def fake_get_chat_model(**kwargs):
            llm.append(kwargs)
            return MagicMock()

        def fake_retriever(**kwargs):
            retrievers.append(kwargs)
            mock = MagicMock()
            mocks.append(mock)
            return mock

        def fake_create_graph(**kwargs):
            graph_kwargs.update(kwargs)
            return MagicMock()

        monkeypatch.setattr(provider, "get_chat_model", fake_get_chat_model)
        monkeypatch.setattr(qdrant_client, "QdrantClient", lambda *a, **k: MagicMock())
        monkeypatch.setattr(embedder_mod, "Embedder", lambda *a, **k: MagicMock())
        monkeypatch.setattr(reranker_mod, "Reranker", lambda *a, **k: MagicMock())
        monkeypatch.setattr(retriever_mod, "HybridRetriever", fake_retriever)
        monkeypatch.setattr(graph_mod, "create_chat_graph", fake_create_graph)
        return SimpleNamespace(
            llm=llm, retrievers=retrievers, mocks=mocks, graph_kwargs=graph_kwargs
        )

    def test_avaliacao_nao_sobrescreve_a_temperatura_do_provedor(self, monkeypatch) -> None:
        """Default None: o provedor impõe temperature=1; sobrescrever quebra o gate ao vivo."""
        from src.evaluation.run_ragas import _carregar_grafo

        reg = self._stub_llm(monkeypatch)
        _carregar_grafo()

        assert len(reg.llm) == 2, "router e agent devem ser criados explicitamente"
        assert [c["temperature"] for c in reg.llm] == [None, None]

    def test_temperature_explícito_chega_ao_provedor(self, monkeypatch) -> None:
        """--temperature é a alavanca para modelos que aceitam temperatura 0."""
        from src.evaluation.run_ragas import _carregar_grafo

        reg = self._stub_llm(monkeypatch)
        _carregar_grafo(temperature=0.2)

        assert [c["temperature"] for c in reg.llm] == [0.2, 0.2]

    def test_avaliacao_da_o_retriever_institucional_ao_agente_documental(
        self, monkeypatch
    ) -> None:
        """Produção tem 2 coleções e a acadêmica tem 0 pontos staff.

        Sem a institucional, o gate media um sistema que não existe.
        """
        from src.evaluation.run_ragas import _carregar_grafo
        from src.rag.settings import RagSettings

        settings = RagSettings()
        reg = self._stub_llm(monkeypatch)
        _carregar_grafo()

        colecoes = {r.get("collection_name") for r in reg.retrievers}
        assert colecoes == {
            settings.qdrant_collection_academico,
            settings.qdrant_collection_institucional,
        }, f"uma retriever por coleção; observado: {colecoes}"

        documental = reg.graph_kwargs.get("documental_retriever")
        assert documental is not None, "o nó documental precisa de retriever próprio"
        assert documental is not reg.graph_kwargs.get("retriever"), (
            "documental não pode herdar a coleção acadêmica: o filtro staff não tem pontos lá"
        )
        for mock in reg.mocks:
            assert mock.build_bm25_index.called, "BM25 é por coleção; sem índice não há fusão"

    def test_pergunta_que_falhou_nao_pontua_como_resposta_ruim(
        self, tmp_path, monkeypatch
    ) -> None:
        """Exceção é abortada, não zerada: número parcial nunca vira métrica publicada."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock

        from langchain_core.messages import AIMessage

        from src.evaluation import run_ragas

        dataset = tmp_path / "dataset.jsonl"
        dataset.write_text(
            "\n".join(
                json.dumps(
                    {
                        "id": f"q00{i}",
                        "profile": "student",
                        "user_id": "ana@demo.usiedu",
                        "question": f"pergunta {i}",
                        "reference_answer": "resposta de referência com conteúdo",
                        "category": "direct",
                        "documents": [],
                    }
                )
                for i in (1, 2)
            ),
            encoding="utf-8",
        )

        graph = MagicMock()
        graph.ainvoke = AsyncMock(
            side_effect=[
                {"messages": [AIMessage(content="resposta de referência com conteúdo")]},
                RuntimeError("timeout do provedor"),
            ]
        )
        monkeypatch.setattr(run_ragas, "_carregar_grafo", lambda *a, **k: graph)

        with pytest.raises(RuntimeError, match="timeout do provedor"):
            asyncio.run(
                run_ragas.executar_avaliacao(
                    dataset, tmp_path / "relatorio.md", None, tmp_path / "ausente.jsonl"
                )
            )

