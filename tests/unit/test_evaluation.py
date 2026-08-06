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
    async def test_executar_avaliacao_gera_relatorio(self, tmp_path) -> None:
        """executar_avaliacao deve gerar relatório para o dataset (limit 2)."""
        from src.evaluation.run_ragas import executar_avaliacao

        output = tmp_path / "relatorio_eval.md"
        resultado = await executar_avaliacao(dataset_path=DATASET_PATH, output_path=output, limit=2)
        assert resultado == output
        assert output.exists()

    def test_main_executa_cli(self, tmp_path, monkeypatch) -> None:
        """main deve executar a CLI com sucesso."""
        from src.evaluation.run_ragas import main

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
