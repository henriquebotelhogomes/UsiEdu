"""Testes determinísticos do baseline e diagnóstico RAG da T02.1."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.evaluation.run_ragas import carregar_dataset

ROOT = Path(__file__).parent.parent.parent
DATASET_PATH = ROOT / "src" / "evaluation" / "dataset.jsonl"
DIAGNOSTICO_PATH = ROOT / "src" / "evaluation" / "baseline_diagnostico_2026-08-06.json"
RELATORIO_PATH = ROOT / "src" / "evaluation" / "relatorio_ragas.md"

CATEGORIAS = {
    "direct",
    "tool",
    "composta",
    "fora_de_escopo",
    "sem_resposta",
}
CAUSAS_ZERO = {
    "fonte_ausente",
    "recuperacao_inadequada",
    "resposta_insuficiente",
    "inadequacao_metrica",
}


def _carregar_diagnostico() -> dict:
    with DIAGNOSTICO_PATH.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def test_diagnostico_tem_schema_versionado_e_taxonomia_completa() -> None:
    """O diagnóstico congela seu schema e as cinco categorias do dataset."""
    diagnostico = _carregar_diagnostico()

    assert diagnostico["schema_version"] == "1.0.0"
    assert diagnostico["baseline"]["source_report"] == "src/evaluation/relatorio_ragas.md"
    assert set(diagnostico["taxonomy"]) == CATEGORIAS

    for categoria, regra in diagnostico["taxonomy"].items():
        assert regra["category"] == categoria
        assert isinstance(regra["report"], str)
        assert regra["report"]


def test_diagnostico_inventaria_dataset_com_ids_unicos_e_schema_valido() -> None:
    """Cada ID q001–q030 aparece uma vez e corresponde ao dataset versionado."""
    dataset = carregar_dataset(DATASET_PATH)
    diagnostico = _carregar_diagnostico()
    inventario = diagnostico["inventory"]

    dataset_por_id = {pergunta["id"]: pergunta for pergunta in dataset}
    ids_inventario = [caso["id"] for caso in inventario]

    assert len(dataset_por_id) == len(dataset)
    assert len(ids_inventario) == len(set(ids_inventario))
    assert set(ids_inventario) == set(dataset_por_id)
    assert set(ids_inventario) == {f"q{numero:03d}" for numero in range(1, 31)}

    for caso in inventario:
        pergunta = dataset_por_id[caso["id"]]
        assert caso["profile"] == pergunta["profile"]
        assert caso["category"] == pergunta["category"]
        assert caso["category"] in CATEGORIAS
        assert set(caso["reported_scores"]) == {"faithfulness", "answer_relevancy"}
        assert all(isinstance(score, (int, float)) for score in caso["reported_scores"].values())
        assert isinstance(caso["evidence"], str)
        assert caso["evidence"]


def test_toda_nota_zero_tem_causa_rastreavel_prevista() -> None:
    """Notas zero do relatório têm causa permitida e evidência sem inferir fatos."""
    inventario = _carregar_diagnostico()["inventory"]

    for caso in inventario:
        tem_nota_zero = any(score == 0 for score in caso["reported_scores"].values())
        if tem_nota_zero:
            assert caso["zero_score_cause"] in CAUSAS_ZERO
        else:
            assert caso["zero_score_cause"] is None


def test_inventario_preserva_scores_do_relatorio_e_registra_categoria_divergente() -> None:
    """O inventário congela os scores e explicita a única divergência de categoria."""
    padrao = re.compile(
        r"^\| (q\d{3}) \| ([^|]+) \| ([^|]+) \| .* \| (\d\.\d{3}) \| (\d\.\d{3}) \|$"
    )
    linhas = RELATORIO_PATH.read_text(encoding="utf-8").splitlines()
    relatorio = {
        correspondencia.group(1): {
            "profile": correspondencia.group(2),
            "category": correspondencia.group(3),
            "faithfulness": float(correspondencia.group(4)),
            "answer_relevancy": float(correspondencia.group(5)),
        }
        for linha in linhas
        if (correspondencia := padrao.match(linha))
    }

    inventario = _carregar_diagnostico()["inventory"]
    assert set(relatorio) == {caso["id"] for caso in inventario}

    for caso in inventario:
        linha = relatorio[caso["id"]]
        assert linha["profile"] == caso["profile"]
        assert linha["faithfulness"] == caso["reported_scores"]["faithfulness"]
        assert linha["answer_relevancy"] == caso["reported_scores"]["answer_relevancy"]
        if caso["id"] == "q022":
            assert linha["category"] == "direct"
            assert caso["category"] == "sem_resposta"
        else:
            assert linha["category"] == caso["category"]
