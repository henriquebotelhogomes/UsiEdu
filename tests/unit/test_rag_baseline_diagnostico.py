"""Testes determinísticos do baseline e diagnóstico RAG da T02.1."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DIAGNOSTICO_PATH = ROOT / "src" / "evaluation" / "baseline_diagnostico_2026-08-06.json"
DOC_QUALIDADE_PATH = ROOT / "docs" / "profissionalizacao" / "02-qualidade-rag.md"
BASELINE_COMMIT = "9f7c9bc73c1def78dd2efc489a022a6541d8ff74"
Q022_REVISION_COMMIT = "80d27c306bcf8c14eb732d13d48d09d0714db2e6"

CATEGORIAS = {
    "direct",
    "tool",
    "composta",
    "fora_de_escopo",
    "sem_resposta",
}


def _carregar_diagnostico() -> dict:
    with DIAGNOSTICO_PATH.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    ).stdout.strip()


def _linhas_relatorio(conteudo: str) -> dict[str, dict[str, str | float]]:
    padrao = re.compile(
        r"^\| (q\d{3}) \| ([^|]+) \| ([^|]+) \| .* \| (\d\.\d{3}) \| (\d\.\d{3}) \|$"
    )
    return {
        correspondencia.group(1): {
            "profile": correspondencia.group(2),
            "category": correspondencia.group(3),
            "faithfulness": float(correspondencia.group(4)),
            "answer_relevancy": float(correspondencia.group(5)),
        }
        for linha in conteudo.splitlines()
        if (correspondencia := padrao.match(linha))
    }


def test_diagnostico_tem_schema_taxonomia_e_proveniencia_historica() -> None:
    """O diagnóstico aponta somente para os blobs da execução histórica."""
    diagnostico = _carregar_diagnostico()
    baseline = diagnostico["baseline"]

    assert diagnostico["schema_version"] == "2.0.0"
    assert set(diagnostico["taxonomy"]) == CATEGORIAS
    assert baseline["source_revision"]["commit"] == BASELINE_COMMIT
    assert baseline["source_revision"]["hash_algorithm"] == "git-blob-sha1"
    assert baseline["source_revision"]["dataset_blob"] == _git(
        "rev-parse", f"{BASELINE_COMMIT}:src/evaluation/dataset.jsonl"
    )
    assert baseline["source_revision"]["manifest_blob"] == _git(
        "rev-parse", f"{BASELINE_COMMIT}:knowledge_base/manifest.json"
    )
    assert baseline["source_revision"]["report_blob"] == _git(
        "rev-parse", f"{BASELINE_COMMIT}:src/evaluation/relatorio_ragas.md"
    )


def test_inventario_tem_ids_unicos_e_corresponde_ao_dataset_historico() -> None:
    """Cada caso q001-q030 vem do dataset que originou o relatório, não do atual."""
    inventario = _carregar_diagnostico()["inventory"]
    dataset_historico = {
        pergunta["id"]: pergunta
        for linha in _git("show", f"{BASELINE_COMMIT}:src/evaluation/dataset.jsonl").splitlines()
        if linha
        for pergunta in [json.loads(linha)]
    }
    ids_inventario = [caso["id"] for caso in inventario]

    assert len(ids_inventario) == len(set(ids_inventario))
    assert (
        set(ids_inventario)
        == set(dataset_historico)
        == {f"q{numero:03d}" for numero in range(1, 31)}
    )

    for caso in inventario:
        pergunta = dataset_historico[caso["id"]]
        assert caso["profile"] == pergunta["profile"]
        assert caso["category"] == pergunta["category"]
        assert caso["category"] in CATEGORIAS
        assert set(caso["reported_scores"]) == {"faithfulness", "answer_relevancy"}


def test_inventario_preserva_scores_do_relatorio_historico() -> None:
    """Scores congelados reproduzem o relatório no mesmo commit de execução."""
    relatorio = _linhas_relatorio(
        _git("show", f"{BASELINE_COMMIT}:src/evaluation/relatorio_ragas.md")
    )
    inventario = _carregar_diagnostico()["inventory"]

    assert set(relatorio) == {caso["id"] for caso in inventario}
    for caso in inventario:
        linha = relatorio[caso["id"]]
        assert linha["profile"] == caso["profile"]
        assert linha["category"] == caso["category"]
        assert linha["faithfulness"] == caso["reported_scores"]["faithfulness"]
        assert linha["answer_relevancy"] == caso["reported_scores"]["answer_relevancy"]


def test_zeros_sao_indeterminados_sem_respostas_ou_erros_brutos() -> None:
    """Não se atribui causa factual quando a execução não preservou saída ou exceção."""
    diagnostico = _carregar_diagnostico()
    execution = diagnostico["baseline"]["execution"]

    assert execution == {
        "declared_mode": "Ragas+LLM",
        "observed_mechanism": "heuristic_scoring",
        "ragas_invocation_observed": False,
        "raw_answers_recorded": False,
        "raw_errors_recorded": False,
        "exception_policy": "zero_metrics",
    }
    for caso in diagnostico["inventory"]:
        if any(score == 0 for score in caso["reported_scores"].values()):
            assert caso["zero_score_cause"] == "indeterminada"
            assert caso["evidence"] == "relatorio historico; resposta e erro bruto indisponiveis."
        else:
            assert caso["zero_score_cause"] is None


def test_q022_posterior_fica_separada_do_snapshot_historico() -> None:
    """A reclassificação posterior de q022 não altera o inventário da execução."""
    diagnostico = _carregar_diagnostico()
    revisao = diagnostico["post_baseline_revisions"]["q022"]
    dataset_historico = {
        pergunta["id"]: pergunta
        for linha in _git("show", f"{BASELINE_COMMIT}:src/evaluation/dataset.jsonl").splitlines()
        if linha
        for pergunta in [json.loads(linha)]
    }
    dataset_posterior = {
        pergunta["id"]: pergunta
        for linha in _git(
            "show", f"{Q022_REVISION_COMMIT}:src/evaluation/dataset.jsonl"
        ).splitlines()
        if linha
        for pergunta in [json.loads(linha)]
    }

    assert revisao["commit"] == Q022_REVISION_COMMIT
    assert revisao["dataset_blob"] == _git(
        "rev-parse", f"{Q022_REVISION_COMMIT}:src/evaluation/dataset.jsonl"
    )
    assert dataset_historico["q022"]["category"] == "direct"
    assert dataset_posterior["q022"]["category"] == "sem_resposta"


def test_t02_1_permanece_parcial_sem_configuracao_factual_do_juiz() -> None:
    """O checklist não conclui T02.1 enquanto faltam parâmetros da execução histórica."""
    conteudo = DOC_QUALIDADE_PATH.read_text(encoding="utf-8")

    assert "| Estado | Em andamento — T02.1 parcial;" in conteudo
    assert "- [~] **T02.1 — Congelar baseline e diagnóstico**" in conteudo
    assert "modelo/configuracao/parametros do juiz historico nao registrados" in conteudo
