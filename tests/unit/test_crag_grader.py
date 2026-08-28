"""Testes unitários para o RetrievalGrader (Corrective RAG - CRAG)."""

from src.rag.crag_grader import RetrievalGrader
from src.rag.models import RetrievalResult, Source


def _make_result(text: str, score: float, doc: str = "Regimento") -> RetrievalResult:
    """Helper para criar instâncias de RetrievalResult nos testes."""
    return RetrievalResult(
        text=text,
        score=score,
        source=Source(
            document=doc,
            section="Capítulo 1",
            excerpt=text,
            url=None,
        ),
    )


class TestRetrievalGrader:
    """Suíte de testes para a lógica de classificação e filtragem do CRAG Grader."""

    def test_todos_resultados_relevantes(self):
        grader = RetrievalGrader(min_relevance_score=0.35)
        results = [
            _make_result("Art. 10 - Matrícula trancada", 0.85),
            _make_result("Art. 11 - Prazos de ajuste", 0.60),
            _make_result("Art. 12 - Critérios de jubilamento", 0.40),
        ]

        approved, has_relevant = grader.grade_results("como trancar matrícula?", results)

        assert has_relevant is True
        assert len(approved) == 3
        assert [r.score for r in approved] == [0.85, 0.60, 0.40]

    def test_filtragem_de_resultados_ruidosos(self):
        grader = RetrievalGrader(min_relevance_score=0.35)
        results = [
            _make_result("Art. 10 - Matrícula trancada", 0.85),
            _make_result("Taxa de emissão de diploma", 0.20),
            _make_result("Art. 11 - Prazos de ajuste", 0.50),
            _make_result("Cardápio do RU", 0.12),
        ]

        approved, has_relevant = grader.grade_results("como trancar matrícula?", results)

        assert has_relevant is True
        assert len(approved) == 2
        assert approved[0].text == "Art. 10 - Matrícula trancada"
        assert approved[1].text == "Art. 11 - Prazos de ajuste"

    def test_todos_resultados_abaixo_do_limiar(self):
        grader = RetrievalGrader(min_relevance_score=0.35)
        results = [
            _make_result("Taxa de emissão de diploma", 0.25),
            _make_result("Cardápio do restaurante universitário", 0.10),
            _make_result("Estacionamento do campus", 0.05),
        ]

        approved, has_relevant = grader.grade_results("qual a regra de física quântica?", results)

        assert has_relevant is False
        assert len(approved) == 0

    def test_lista_vazia(self):
        grader = RetrievalGrader(min_relevance_score=0.35)
        approved, has_relevant = grader.grade_results("qualquer busca", [])

        assert has_relevant is False
        assert approved == []

    def test_grader_desabilitado(self):
        grader = RetrievalGrader(min_relevance_score=0.35, enabled=False)
        results = [
            _make_result("Documento de baixa relevância", 0.10),
        ]

        approved, has_relevant = grader.grade_results("teste", results)

        assert has_relevant is True
        assert len(approved) == 1
        assert approved[0].score == 0.10

    def test_override_min_score_customizado(self):
        grader = RetrievalGrader(min_relevance_score=0.35)
        results = [
            _make_result("Doc razoável", 0.40),
            _make_result("Doc muito bom", 0.75),
        ]

        # Com min_score mais rígido de 0.60
        approved, has_relevant = grader.grade_results("teste", results, min_score=0.60)

        assert has_relevant is True
        assert len(approved) == 1
        assert approved[0].score == 0.75
