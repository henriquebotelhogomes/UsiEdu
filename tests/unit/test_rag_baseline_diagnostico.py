"""Testes determinísticos e autocontidos do baseline RAG da T02.1."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DIAGNOSTICO_PATH = ROOT / "src" / "evaluation" / "baseline_diagnostico_2026-08-06.json"
DOC_QUALIDADE_PATH = ROOT / "docs" / "profissionalizacao" / "02-qualidade-rag.md"
SNAPSHOT_DIR = ROOT / "src" / "evaluation" / "baseline_snapshots" / "2026-08-06"

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


def _blob_git(path: Path) -> str:
    """Calcula ID Git com bytes UTF-8 e LF canônicos, independente do checkout."""
    conteudo = path.read_bytes().replace(b"\r\n", b"\n")
    cabecalho = f"blob {len(conteudo)}\0".encode()
    return hashlib.sha1(cabecalho + conteudo, usedforsecurity=False).hexdigest()


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


def test_diagnostico_tem_schema_taxonomia_e_snapshots_historicos() -> None:
    """O diagnóstico registra blobs canônicos calculados dos snapshots versionados."""
    diagnostico = _carregar_diagnostico()
    origem = diagnostico["baseline"]["source_revision"]

    assert diagnostico["schema_version"] == "2.0.0"
    assert set(diagnostico["taxonomy"]) == CATEGORIAS
    assert origem["hash_algorithm"] == "git-blob-sha1"
    for artefato, nome in {
        "dataset": "dataset.jsonl",
        "manifest": "manifest.json",
        "report": "relatorio_ragas.md",
    }.items():
        assert origem[f"{artefato}_snapshot_path"] == (
            f"src/evaluation/baseline_snapshots/2026-08-06/{nome}"
        )
        assert origem[f"{artefato}_snapshot_blob"] == _blob_git(SNAPSHOT_DIR / nome)


def test_inventario_tem_ids_unicos_e_corresponde_ao_dataset_snapshot() -> None:
    """Cada q001-q030 vem do dataset que produziu o relatório histórico."""
    inventario = _carregar_diagnostico()["inventory"]
    dataset_historico = {
        pergunta["id"]: pergunta
        for linha in (SNAPSHOT_DIR / "dataset.jsonl").read_text(encoding="utf-8").splitlines()
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


def test_inventario_preserva_scores_do_relatorio_snapshot() -> None:
    """Scores congelados reproduzem o relatório versionado no repositório."""
    relatorio = _linhas_relatorio((SNAPSHOT_DIR / "relatorio_ragas.md").read_text(encoding="utf-8"))
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
    historico = {
        pergunta["id"]: pergunta
        for linha in (SNAPSHOT_DIR / "dataset.jsonl").read_text(encoding="utf-8").splitlines()
        if linha
        for pergunta in [json.loads(linha)]
    }
    posterior_path = SNAPSHOT_DIR / "dataset_q022_reclassificado.jsonl"
    posterior = {
        pergunta["id"]: pergunta
        for linha in posterior_path.read_text(encoding="utf-8").splitlines()
        if linha
        for pergunta in [json.loads(linha)]
    }

    assert revisao["dataset_blob_snapshot"] == (
        "src/evaluation/baseline_snapshots/2026-08-06/dataset_q022_reclassificado.jsonl"
    )
    assert revisao["snapshot_blob"] == _blob_git(posterior_path)
    assert historico["q022"]["category"] == "direct"
    assert posterior["q022"]["category"] == "sem_resposta"


def test_t02_1_permanece_parcial_sem_metadados_factualmente_ausentes() -> None:
    """O checklist não conclui T02.1 enquanto faltam artefatos de execução históricos."""
    conteudo = DOC_QUALIDADE_PATH.read_text(encoding="utf-8")

    assert "| Estado | Em andamento — T02.1 parcial;" in conteudo
    assert "- [~] **T02.1 — Congelar baseline e diagnóstico**" in conteudo
    assert "modelo/configuracao/parametros do juiz historico nao registrados" in conteudo
    contexto = conteudo.split("## 2. Objetivo mensurável", maxsplit=1)[0]
    assert "lacuna real de corpus" not in contexto
    assert "redirecionamento correto" not in contexto
