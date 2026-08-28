"""Testes unitários para o gerador sintético de testes (SyntheticTestsetGenerator)."""

import json
from pathlib import Path

from scripts.generate_synthetic_testset import SyntheticTestsetGenerator
from src.rag.models import Chunk


def _make_sample_chunks() -> list[Chunk]:
    """Cria lista de chunks simulados para os testes unitários."""
    return [
        Chunk(
            id="c01",
            text="Art. 15 O trancamento pode ser solicitado pelo discente até a 4ª semana.",
            metadata={
                "instituicao": "UnB",
                "documento": "Regimento Geral da UnB",
                "secao": "Art. 15",
                "publico_alvo": "student",
            },
        ),
        Chunk(
            id="c02",
            text="Art. 16 O limite máximo de trancamentos durante o curso é de 4 semestres.",
            metadata={
                "instituicao": "UnB",
                "documento": "Regimento Geral da UnB",
                "secao": "Art. 16",
                "publico_alvo": "student",
            },
        ),
        Chunk(
            id="c03",
            text="CAPÍTULO III O servidor docente terá direito a licença para capacitação.",
            metadata={
                "instituicao": "UnB",
                "documento": "Guia do Servidor UnB",
                "secao": "CAPÍTULO III",
                "publico_alvo": "staff",
            },
        ),
        Chunk(
            id="c04",
            text="SEÇÃO II A avaliação de estágio probatório ocorre nos primeiros 36 meses.",
            metadata={
                "instituicao": "UnB",
                "documento": "Guia do Servidor UnB",
                "secao": "SEÇÃO II",
                "publico_alvo": "staff",
            },
        ),
    ]


class TestSyntheticTestsetGenerator:
    """Suíte de testes para o gerador sintético de dataset."""

    def test_geracao_dataset_contagem_e_estrutura(self):
        chunks = _make_sample_chunks()
        gen = SyntheticTestsetGenerator()

        dataset = gen.generate_testset(chunks, count=10, seed=123)

        assert len(dataset) == 10
        valid_cats = ("direct", "reasoning", "multi_context", "fora_de_escopo", "sem_resposta")
        for item in dataset:
            assert "id" in item
            assert item["id"].startswith("synth_")
            assert "question" in item
            assert len(item["question"]) > 5
            assert "reference_answer" in item
            assert len(item["reference_answer"]) > 5
            assert "category" in item
            assert item["category"] in valid_cats
            assert "documents" in item

    def test_distribuicao_de_categorias(self):
        chunks = _make_sample_chunks()
        gen = SyntheticTestsetGenerator()

        dataset = gen.generate_testset(chunks, count=20, seed=42)

        categories = {item["category"] for item in dataset}
        assert "direct" in categories
        assert "reasoning" in categories
        assert "multi_context" in categories

    def test_salvar_testset_jsonl(self, tmp_path: Path):
        chunks = _make_sample_chunks()
        gen = SyntheticTestsetGenerator()
        dataset = gen.generate_testset(chunks, count=5, seed=99)

        output_file = tmp_path / "synthetic_test.jsonl"
        gen.save_testset(dataset, output_file)

        assert output_file.exists()
        lines = output_file.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 5

        first_obj = json.loads(lines[0])
        assert first_obj["id"] == "synth_001"
        assert "question" in first_obj
