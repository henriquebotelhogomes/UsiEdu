"""Contrato determinístico da comparação de juízes da T02.5."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.evaluation.judge_comparison import (
    build_evaluation_items,
    build_input_fingerprint,
    summarize_comparison,
    validate_comparison_config,
)

ROOT = Path(__file__).parent.parent.parent
CONFIG_PATH = ROOT / "src" / "evaluation" / "judge_comparison" / "config.json"
RUN_DIR = CONFIG_PATH.parent / "2026-08-11"


def _config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _records(score_by_judge: dict[str, float]) -> list[dict]:
    records = []
    for judge, score in score_by_judge.items():
        for repetition in range(1, 4):
            records.append(
                {
                    "schema_version": "1.0.0",
                    "comparison_id": "judge-comparison-2026-08-11",
                    "judge": judge,
                    "model": ("deepseek-v4-flash" if judge == "economic" else "kimi-k2.7-code"),
                    "case_id": "q001",
                    "subquestion_id": "q001.rag",
                    "repetition": repetition,
                    "attempt_count": 1,
                    "scores": {
                        "faithfulness": score,
                        "context_precision": score,
                        "context_recall": score,
                        "answer_relevancy": score,
                    },
                    "rationale": "Racional rastreável.",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 20,
                        "total_tokens": 120,
                    },
                    "estimated_cost_usd": 0.001,
                }
            )
    return records


def test_config_fixa_paridade_repeticoes_temperatura_e_orcamento() -> None:
    config = _config()
    validate_comparison_config(config, ROOT)

    assert config["protocol"]["repetitions"] == 3
    assert config["protocol"]["requested_temperature"] == 0
    assert config["protocol"]["effective_temperature"] == 1
    assert config["protocol"]["temperature_zero_supported"] is False
    assert "only 1 is allowed" in config["protocol"]["temperature_limitation"]
    assert config["protocol"]["budget_usd"] == 5.0
    assert config["protocol"]["max_attempts"] == 2
    assert config["judges"]["economic"]["model"] == "deepseek-v4-flash"
    assert config["judges"]["strong"]["model"] == "kimi-k2.7-code"
    assert config["inputs"]["dataset_path"] == "src/evaluation/dataset.jsonl"
    assert config["inputs"]["manifest_path"] == (
        "src/evaluation/baseline_runs/2026-08-11/manifest.json"
    )
    assert config["inputs"]["slice_contract_path"] == ("src/evaluation/recortes_avaliacao_v1.json")


@pytest.mark.parametrize(
    "field",
    ["dataset_git_blob_sha1", "manifest_git_blob_sha1", "slice_contract_git_blob_sha1"],
)
def test_config_rejeita_hash_de_entrada_divergente(field: str) -> None:
    config = _config()
    config["inputs"][field] = "0" * 40

    with pytest.raises(ValueError, match=field):
        validate_comparison_config(config, ROOT)


def test_itens_usam_exatamente_o_recorte_rag_versionado() -> None:
    config = _config()
    items = build_evaluation_items(config, ROOT)
    contract = json.loads(
        (ROOT / config["inputs"]["slice_contract_path"]).read_text(encoding="utf-8")
    )
    expected_ids = [
        subquestion["id"]
        for case in contract["cases"]
        for subquestion in case["subquestions"]
        if subquestion["requires_retrieval"]
    ]

    assert [item["subquestion_id"] for item in items] == expected_ids
    assert len(items) == 17
    assert {item["case_id"] for item in items if item["case_id"] == "q030"} == {"q030"}
    assert all(item["answer"] is not None for item in items)


def test_resumo_rejeita_repeticao_ausente_e_score_booleano() -> None:
    config = _config()
    fingerprint = build_input_fingerprint(config)
    records = _records({"economic": 0.8, "strong": 0.82})

    with pytest.raises(ValueError, match="repeticoes"):
        summarize_comparison(records[:-1], config, fingerprint)

    invalid = copy.deepcopy(records)
    invalid[0]["scores"]["faithfulness"] = True
    with pytest.raises(ValueError, match="faithfulness"):
        summarize_comparison(invalid, config, fingerprint)


def test_resumo_calcula_agregados_divergencia_estabilidade_e_custo() -> None:
    config = _config()
    fingerprint = build_input_fingerprint(config)
    report = summarize_comparison(
        _records({"economic": 0.8, "strong": 0.82}),
        config,
        fingerprint,
    )

    assert report["record_count"] == 6
    assert report["estimated_cost_usd"] == pytest.approx(0.006)
    assert report["judges"]["economic"]["aggregate_scores"]["faithfulness"] == pytest.approx(0.8)
    assert report["judges"]["strong"]["aggregate_scores"]["faithfulness"] == pytest.approx(0.82)
    assert report["divergence"]["faithfulness"]["absolute"] == pytest.approx(0.02)
    assert report["stability"]["economic"]["faithfulness"]["range"] == pytest.approx(0.0)
    assert report["stability"]["strong"]["faithfulness"]["range"] == pytest.approx(0.0)
    assert report["input_fingerprint"] == fingerprint
    assert report["decision"] == "maintain_economic_pending_human_calibration"


def test_real_comparison_is_complete_recalculable_and_within_budget() -> None:
    config = _config()
    records = [
        json.loads(line)
        for line in (RUN_DIR / "records.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    persisted_report = json.loads((RUN_DIR / "report.json").read_text(encoding="utf-8"))

    assert len(records) == 2 * 17 * 3 == 102
    assert {
        (record["judge"], record["subquestion_id"], record["repetition"]) for record in records
    } == {
        (judge, subquestion_id, repetition)
        for judge in ("economic", "strong")
        for subquestion_id in [
            item["subquestion_id"] for item in build_evaluation_items(config, ROOT)
        ]
        for repetition in range(1, 4)
    }
    assert persisted_report == summarize_comparison(
        records,
        config,
        build_input_fingerprint(config),
    )
    assert persisted_report["estimated_cost_usd"] == pytest.approx(0.31951975)
    assert persisted_report["estimated_cost_usd"] < persisted_report["budget_usd"] == 5.0
    assert persisted_report["decision"] == "maintain_economic_pending_human_calibration"
    assert persisted_report["divergence"]["faithfulness"]["absolute"] == pytest.approx(
        0.20980392156862748
    )
    assert persisted_report["divergence"]["answer_relevancy"]["absolute"] == pytest.approx(
        0.14411764705882346
    )


def test_documentation_records_t02_5_evidence_without_claiming_p1_complete() -> None:
    document = (ROOT / "docs" / "profissionalizacao" / "02-qualidade-rag.md").read_text(
        encoding="utf-8"
    )

    assert "T02.1–T02.5 concluídas; gates hospedado e operacional pendentes" in document
    assert "- [x] **T02.5 — Comparar juízes**" in document
    assert "US$ 0,319520" in document
    assert "temperatura efetiva 1" in document
    assert "manter provisoriamente o DeepSeek V4 Flash" in document
    assert "| G5 — Encerramento | Não iniciado |" in document
