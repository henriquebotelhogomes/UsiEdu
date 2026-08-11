"""Contrato determinístico do novo baseline auditável da T02.1b."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.auditable_baseline import (
    METRIC_NAMES,
    BudgetExceededError,
    canonical_git_blob_sha1,
    compute_aggregate_scores,
    estimate_cost_usd,
    load_run_records,
    validate_run_record,
)

ROOT = Path(__file__).parent.parent.parent
DATASET_PATH = ROOT / "src" / "evaluation" / "dataset.jsonl"
MANIFEST_PATH = ROOT / "knowledge_base" / "manifest.json"
CONFIG_PATH = ROOT / "src" / "evaluation" / "baseline_runs" / "2026-08-11" / "config.json"


def _record(**overrides: object) -> dict:
    record = {
        "schema_version": "1.0.0",
        "run_id": "baseline-2026-08-11",
        "case_id": "q001",
        "profile": "student",
        "category": "direct",
        "question": "Pergunta?",
        "reference_answer": "Resposta esperada.",
        "started_at": "2026-08-11T22:00:00+00:00",
        "duration_ms": 123,
        "status": "success",
        "answer": "Resposta observada.",
        "sources": [],
        "delegations": ["academico"],
        "error": None,
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "by_model": {
                "deepseek-v4-flash": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                }
            },
        },
        "estimated_cost_usd": 0.0000021,
        "scores": {
            "faithfulness": 0.8,
            "context_precision": 0.7,
            "context_recall": 0.6,
            "answer_relevancy": 0.9,
        },
        "score_mechanism": "legacy_keyword_heuristic",
    }
    record.update(overrides)
    return record


def test_registro_de_execucao_exige_schema_completo() -> None:
    validate_run_record(_record())

    incomplete = _record()
    del incomplete["answer"]
    with pytest.raises(ValueError, match="campos"):
        validate_run_record(incomplete)


@pytest.mark.parametrize(
    "field,value",
    [
        ("duration_ms", True),
        ("estimated_cost_usd", True),
    ],
)
def test_registro_rejeita_bool_em_campos_numericos(field: str, value: bool) -> None:
    with pytest.raises(ValueError, match=field):
        validate_run_record(_record(**{field: value}))


def test_registro_rejeita_bool_em_scores_e_tokens() -> None:
    record = _record()
    record["scores"]["faithfulness"] = True
    with pytest.raises(ValueError, match="faithfulness"):
        validate_run_record(record)

    record = _record()
    record["usage"]["input_tokens"] = False
    with pytest.raises(ValueError, match="input_tokens"):
        validate_run_record(record)


def test_status_de_erro_preserva_excecao_e_nao_inventa_saida() -> None:
    validate_run_record(
        _record(
            status="error",
            answer=None,
            sources=[],
            error={"type": "RuntimeError", "message": "falha rastreavel"},
            scores={name: None for name in METRIC_NAMES},
        )
    )

    with pytest.raises(ValueError, match="error"):
        validate_run_record(_record(status="error", answer=None, error=None))


def test_jsonl_detecta_ids_duplicados_antes_de_indexar(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(
        "\n".join(json.dumps(_record()) for _ in range(2)) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicado.*q001"):
        load_run_records(path)


def test_agregados_derivam_apenas_de_casos_com_sucesso() -> None:
    first = _record()
    second = _record(
        case_id="q002",
        scores={
            "faithfulness": 0.4,
            "context_precision": 0.3,
            "context_recall": 0.2,
            "answer_relevancy": 0.1,
        },
    )
    failed = _record(
        case_id="q003",
        status="error",
        answer=None,
        error={"type": "TimeoutError", "message": "timeout"},
        scores={name: None for name in METRIC_NAMES},
    )

    assert compute_aggregate_scores([first, second, failed]) == {
        "faithfulness": 0.6,
        "context_precision": 0.5,
        "context_recall": 0.4,
        "answer_relevancy": 0.5,
    }


def test_custo_estimado_e_teto_sao_deterministicos() -> None:
    rates = {
        "deepseek-v4-flash": {
            "input_per_million_usd": 0.07,
            "output_per_million_usd": 0.14,
        }
    }
    usage = {
        "by_model": {
            "deepseek-v4-flash": {
                "input_tokens": 1_000_000,
                "output_tokens": 1_000_000,
                "total_tokens": 2_000_000,
            }
        }
    }
    assert estimate_cost_usd(usage, rates, budget_usd=0.21) == pytest.approx(0.21)
    with pytest.raises(BudgetExceededError):
        estimate_cost_usd(usage, rates, budget_usd=0.20)


def test_hash_git_canonico_independe_de_crlf(tmp_path: Path) -> None:
    lf = tmp_path / "lf"
    crlf = tmp_path / "crlf"
    lf.write_bytes(b"linha 1\nlinha 2\n")
    crlf.write_bytes(b"linha 1\r\nlinha 2\r\n")
    assert canonical_git_blob_sha1(lf) == canonical_git_blob_sha1(crlf)


def test_dataset_e_manifest_atuais_tem_hash_canonico() -> None:
    assert canonical_git_blob_sha1(DATASET_PATH)
    assert canonical_git_blob_sha1(MANIFEST_PATH)


def test_configuracao_fixa_modelos_orcamento_e_sem_tracing_externo() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

    assert config["schema_version"] == "1.0.0"
    assert config["run_id"] == "baseline-2026-08-11"
    assert config["models"] == {
        "router": {
            "provider": "opencode-go",
            "name": "deepseek-v4-flash",
            "temperature": 1.0,
            "max_output_tokens": 2048,
        },
        "agent": {
            "provider": "opencode-go",
            "name": "deepseek-v4-pro",
            "temperature": 1.0,
            "max_output_tokens": 2048,
        },
    }
    assert config["budget"] == {
        "total_usd": 5.0,
        "per_case_reserve_usd": 0.25,
        "cost_kind": "token_equivalent_estimate",
    }
    assert config["scoring"]["ragas_invocation"] is False
    assert config["observability"]["external_tracing"] is False
