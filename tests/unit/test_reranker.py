"""Testes unitários para o reranker cross-encoder."""

import pytest
import sentence_transformers

from src.rag.reranker import Reranker


class FakeCrossEncoder:
    """CrossEncoder fake: score 1.0 se a janela contém 'feriado', senão 0.1."""

    instances: list = []

    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        self.last_pairs = None
        FakeCrossEncoder.instances.append(self)

    def predict(self, pairs):
        self.last_pairs = pairs
        return [1.0 if "feriado" in doc else 0.1 for _, doc in pairs]


@pytest.fixture(autouse=True)
def fake_cross_encoder(monkeypatch):
    """Substitui o CrossEncoder real pelo fake em todos os testes."""
    FakeCrossEncoder.instances = []
    monkeypatch.setattr(sentence_transformers, "CrossEncoder", FakeCrossEncoder)


class TestInit:
    """Testes de inicialização lazy do modelo."""

    def test_modelo_nao_carregado_no_construtor(self):
        r = Reranker()
        assert r._model is None
        assert FakeCrossEncoder.instances == []

    def test_modelo_carregado_no_primeiro_rerank(self):
        r = Reranker()
        r.rerank("query", ["texto"])
        assert len(FakeCrossEncoder.instances) == 1
        assert FakeCrossEncoder.instances[0].model_name == "BAAI/bge-reranker-base"

    def test_modelo_reutilizado_entre_chamadas(self):
        r = Reranker()
        r.rerank("q1", ["texto um"])
        r.rerank("q2", ["texto dois"])
        assert len(FakeCrossEncoder.instances) == 1


class TestRerank:
    """Testes do reranking por janelas."""

    def test_documentos_vazios_retorna_vazio(self):
        r = Reranker()
        assert r.rerank("query", []) == []

    def test_ordena_por_score_descendente(self):
        r = Reranker()
        docs = ["texto sem palavra-chave", "calendário com feriado nacional"]
        result = r.rerank("feriados", docs)
        assert result[0] == (1, 1.0)
        assert result[1] == (0, 0.1)

    def test_top_k_limita_resultados(self):
        r = Reranker()
        docs = [f"documento {i}" for i in range(6)]
        result = r.rerank("query", docs, top_k=3)
        assert len(result) == 3

    def test_documento_longo_score_da_melhor_janela(self):
        """Documento maior que a janela: score final = melhor janela."""
        r = Reranker(window_chars=30, overlap_chars=5)
        # 'feriado' só aparece no final do texto → além da primeira janela
        doc = "x" * 60 + " feriado " + "y" * 10
        result = r.rerank("feriados", [doc])
        assert result[0][0] == 0
        assert result[0][1] == 1.0

    def test_scores_numpy_com_tolist(self, monkeypatch):
        """predict retornando objeto com .tolist() (ex.: np.ndarray)."""

        class _Array:
            def __init__(self, values):
                self._values = values

            def tolist(self):
                return self._values

        class ToListEncoder(FakeCrossEncoder):
            def predict(self, pairs):
                return _Array([0.5] * len(pairs))

        monkeypatch.setattr(sentence_transformers, "CrossEncoder", ToListEncoder)
        r = Reranker()
        result = r.rerank("query", ["doc um", "doc dois"])
        assert all(score == 0.5 for _, score in result)

    def test_score_escalar_para_par_unico(self, monkeypatch):
        """predict retornando um escalar quando há um único par."""

        class ScalarEncoder(FakeCrossEncoder):
            def predict(self, pairs):
                return 0.7

        monkeypatch.setattr(sentence_transformers, "CrossEncoder", ScalarEncoder)
        r = Reranker()
        result = r.rerank("query", ["doc único"])
        assert result == [(0, 0.7)]


class TestWindows:
    """Testes da divisão em janelas sobrepostas."""

    def test_texto_curto_janela_unica(self):
        r = Reranker(window_chars=100)
        assert r._windows("texto curto") == ["texto curto"]

    def test_texto_longo_multiplas_janelas_com_overlap(self):
        r = Reranker(window_chars=20, overlap_chars=5)
        windows = r._windows("a" * 50)
        assert len(windows) >= 3
        assert all(len(w) <= 20 for w in windows)
        # Janelas cobrem todo o texto
        assert windows[0].startswith("a")
