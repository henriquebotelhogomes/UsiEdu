"""Testes determinísticos e autocontidos do baseline RAG da T02.1."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
DIAGNOSTICO_PATH = ROOT / "src" / "evaluation" / "baseline_diagnostico_2026-08-06.json"
DOC_QUALIDADE_PATH = ROOT / "docs" / "profissionalizacao" / "02-qualidade-rag.md"
SNAPSHOT_DIR = ROOT / "src" / "evaluation" / "baseline_snapshots" / "2026-08-06"

HISTORICAL_COMMIT = "9f7c9bc73c1def78dd2efc489a022a6541d8ff74"
Q022_REVISION_COMMIT = "80d27c306bcf8c14eb732d13d48d09d0714db2e6"
HISTORICAL_BLOBS = {
    "dataset": "7d643a666021218443598288c5c8f5acc5b7ef81",
    "manifest": "d49071f2c96a856f52cfc610adce7e02f9886d91",
    "report": "6e9bcfccbcdc1e455ce193cb8bd704e80d416840",
}
HISTORICAL_AGGREGATES = {
    "faithfulness": 0.565,
    "context_precision": 0.645,
    "context_recall": 0.645,
    "answer_relevancy": 0.565,
}
CATEGORIAS = {
    "direct",
    "tool",
    "composta",
    "fora_de_escopo",
    "sem_resposta",
}
PERFIS = {"student", "staff"}
Q022_HISTORICA = {
    "category": "direct",
    "documents": ["Documentos Institucionais"],
    "reference_answer": (
        "As normas de uso dos laboratórios estão descritas nos manuais institucionais, "
        "com regras de acesso, agendamento e responsabilidade."
    ),
}
Q022_POSTERIOR = {
    "category": "sem_resposta",
    "documents": [],
    "reference_answer": (
        "Não encontrei essa informação nos documentos oficiais indexados "
        "(Guia do Servidor UnB não cobre uso de laboratórios). Recomendo procurar "
        "a pró-reitoria de infraestrutura ou o setor responsável pela gestão de espaços."
    ),
}


def _carregar_diagnostico() -> dict:
    with DIAGNOSTICO_PATH.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _blob_git(path: Path) -> str:
    """Calcula ID Git com bytes UTF-8 e LF canônicos, independente do checkout."""
    conteudo = path.read_bytes().replace(b"\r\n", b"\n")
    cabecalho = f"blob {len(conteudo)}\0".encode()
    return hashlib.sha1(cabecalho + conteudo, usedforsecurity=False).hexdigest()


def _dataset_snapshot(nome: str) -> list[dict]:
    return [
        json.loads(linha)
        for linha in (SNAPSHOT_DIR / nome).read_text(encoding="utf-8").splitlines()
        if linha
    ]


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


def _metricas_agregadas_relatorio(conteudo: str) -> dict[str, float]:
    padrao = re.compile(
        r"^\| (faithfulness|context_precision|"
        r"context_recall|answer_relevancy) \| .* \| (\d\.\d{3}) \|"
    )
    return {
        correspondencia.group(1): float(correspondencia.group(2))
        for linha in conteudo.splitlines()
        if (correspondencia := padrao.match(linha))
    }


def test_proveniencia_e_blobs_historicos_sao_estruturais_e_imutaveis() -> None:
    """Os snapshots canônicos reproduzem exatamente os blobs históricos registrados."""
    diagnostico = _carregar_diagnostico()
    origem = diagnostico["baseline"]["source_revision"]

    assert diagnostico["schema_version"] == "2.0.0"
    assert origem["commit"] == HISTORICAL_COMMIT
    assert origem["hash_algorithm"] == "git-blob-sha1"
    for artefato, nome in {
        "dataset": "dataset.jsonl",
        "manifest": "manifest.json",
        "report": "relatorio_ragas.md",
    }.items():
        assert origem[f"historical_{artefato}_blob"] == HISTORICAL_BLOBS[artefato]
        assert origem[f"{artefato}_snapshot_path"] == (
            f"src/evaluation/baseline_snapshots/2026-08-06/{nome}"
        )
        assert origem[f"{artefato}_snapshot_blob"] == HISTORICAL_BLOBS[artefato]
        assert _blob_git(SNAPSHOT_DIR / nome) == HISTORICAL_BLOBS[artefato]


def test_taxonomia_tem_schema_completo_e_coerente_com_inventario() -> None:
    """A taxonomia define cada categoria referenciada e não admite causa fora do schema."""
    diagnostico = _carregar_diagnostico()
    taxonomy = diagnostico["taxonomy"]
    inventory = diagnostico["inventory"]

    assert set(taxonomy) == CATEGORIAS
    for categoria, regra in taxonomy.items():
        assert set(regra) == {"category", "report"}
        assert isinstance(regra["category"], str)
        assert regra["category"] == categoria
        assert regra["category"] in CATEGORIAS
        assert isinstance(regra["report"], str)
        assert regra["report"]

    assert {caso["category"] for caso in inventory} <= set(taxonomy)
    assert {caso["zero_score_cause"] for caso in inventory} <= {None, "indeterminada"}


def test_inventario_tem_schema_completo_ids_unicos_e_relacoes_validas() -> None:
    """O inventário exige campos, tipos, enums e relações antes de usar IDs como chave."""
    inventario = _carregar_diagnostico()["inventory"]
    dataset_historico = _dataset_snapshot("dataset.jsonl")
    ids_inventario = [caso["id"] for caso in inventario]
    ids_dataset = [pergunta["id"] for pergunta in dataset_historico]

    assert isinstance(inventario, list)
    assert len(ids_inventario) == len(set(ids_inventario))
    assert len(ids_dataset) == len(set(ids_dataset))
    assert set(ids_inventario) == set(ids_dataset) == {f"q{numero:03d}" for numero in range(1, 31)}

    dataset_por_id = {pergunta["id"]: pergunta for pergunta in dataset_historico}
    campos = {"id", "profile", "category", "reported_scores", "zero_score_cause", "evidence"}
    for caso in inventario:
        assert set(caso) == campos
        assert re.fullmatch(r"q\d{3}", caso["id"])
        assert caso["profile"] in PERFIS
        assert caso["category"] in CATEGORIAS
        assert set(caso["reported_scores"]) == {"faithfulness", "answer_relevancy"}
        assert all(
            not isinstance(score, bool) and isinstance(score, (int, float)) and 0.0 <= score <= 1.0
            for score in caso["reported_scores"].values()
        )
        assert caso["zero_score_cause"] in {None, "indeterminada"}
        assert isinstance(caso["evidence"], str) and caso["evidence"]
        assert caso["profile"] == dataset_por_id[caso["id"]]["profile"]
        assert caso["category"] == dataset_por_id[caso["id"]]["category"]


def test_scores_individuais_e_agregados_reproduzem_relatorio_historico() -> None:
    """Scores por caso e as quatro métricas agregadas são verificados contra o snapshot."""
    diagnostico = _carregar_diagnostico()
    conteudo = (SNAPSHOT_DIR / "relatorio_ragas.md").read_text(encoding="utf-8")
    relatorio = _linhas_relatorio(conteudo)
    inventario = diagnostico["inventory"]

    assert diagnostico["baseline"]["aggregate_scores"] == HISTORICAL_AGGREGATES
    assert set(diagnostico["baseline"]["aggregate_scores"]) == set(HISTORICAL_AGGREGATES)
    assert all(
        not isinstance(score, bool) and isinstance(score, (int, float)) and 0.0 <= score <= 1.0
        for score in diagnostico["baseline"]["aggregate_scores"].values()
    )
    assert _metricas_agregadas_relatorio(conteudo) == HISTORICAL_AGGREGATES
    assert set(relatorio) == {caso["id"] for caso in inventario}
    assert Counter(linha["category"] for linha in relatorio.values()) == Counter(
        caso["category"] for caso in inventario
    )
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


def test_q022_historica_e_revisao_posterior_sao_independentes_e_exatas() -> None:
    """A revisão posterior é validada contra constantes, não contra o inventário atual."""
    diagnostico = _carregar_diagnostico()
    revisao = diagnostico["post_baseline_revisions"]["q022"]
    historico = {pergunta["id"]: pergunta for pergunta in _dataset_snapshot("dataset.jsonl")}
    posterior = {
        pergunta["id"]: pergunta
        for pergunta in _dataset_snapshot("dataset_q022_reclassificado.jsonl")
    }
    posterior_path = SNAPSHOT_DIR / "dataset_q022_reclassificado.jsonl"

    assert revisao == {
        "commit": Q022_REVISION_COMMIT,
        "historical_dataset_blob": "67933038582591b4009f9b2aba1286bf85a4ada3",
        "dataset_blob_snapshot": (
            "src/evaluation/baseline_snapshots/2026-08-06/dataset_q022_reclassificado.jsonl"
        ),
        "snapshot_blob": "808ac51aee250822f9baed3f79db164f10e5bcba",
        "change": "q022 category changed from direct to sem_resposta after the baseline report.",
    }
    assert _blob_git(posterior_path) == revisao["snapshot_blob"]
    assert {chave: historico["q022"][chave] for chave in Q022_HISTORICA} == Q022_HISTORICA
    assert {chave: posterior["q022"][chave] for chave in Q022_POSTERIOR} == Q022_POSTERIOR


def test_t02_1_permanece_parcial_sem_metadados_factualmente_ausentes() -> None:
    """O checklist não conclui T02.1 enquanto faltam artefatos de execução históricos."""
    conteudo = DOC_QUALIDADE_PATH.read_text(encoding="utf-8")
    contexto = conteudo.split("## 2. Objetivo mensurável", maxsplit=1)[0]

    assert "| Estado | Em andamento — T02.1 parcial;" in conteudo
    assert "- [~] **T02.1 — Congelar baseline e diagnóstico**" in conteudo
    assert "modelo/configuracao/parametros do juiz historico nao registrados" in conteudo
    assert "lacuna real de corpus" not in contexto
    assert "redirecionamento correto" not in contexto
