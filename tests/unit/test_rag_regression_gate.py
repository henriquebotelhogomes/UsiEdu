"""Contrato determinístico do gate de regressão RAG da T02.4."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.auditable_baseline import canonical_git_blob_sha1
from src.evaluation.regression_gate import compare_evaluations, load_evaluation_summary

ROOT = Path(__file__).parent.parent.parent
POLICY_PATH = ROOT / "src" / "evaluation" / "regression_policy_v1.json"
FIXTURE_DIR = ROOT / "src" / "evaluation" / "regression_fixtures"

METRICS = {
    "faithfulness",
    "context_precision",
    "context_recall",
    "answer_relevancy",
}
RAG_IDS = [
    "q001.rag",
    "q002.rag",
    "q003.rag",
    "q011.rag",
    "q012.rag",
    "q013.rag",
    "q014.rag",
    "q015.rag",
    "q016.rag",
    "q017.rag",
    "q018.rag",
    "q019.rag",
    "q020.rag",
    "q021.rag",
    "q023.teletrabalho",
    "q030.seguranca",
    "q030.treinamentos",
]


def _summary(
    *,
    run_id: str,
    score: float = 0.8,
    dataset_blob: str = "1" * 40,
    manifest_blob: str = "2" * 40,
    contract_blob: str = "3" * 40,
    special_passed: int = 4,
) -> dict:
    return {
        "schema_version": "1.0.0",
        "evidence_kind": "gate_self_test",
        "run_id": run_id,
        "dataset_git_blob_sha1": dataset_blob,
        "manifest_git_blob_sha1": manifest_blob,
        "slice_contract_git_blob_sha1": contract_blob,
        "taxonomy_version": "1.0.0",
        "score_mechanism": "deterministic_fixture",
        "rag_respondible": {
            "subquestion_ids": list(RAG_IDS),
            "aggregate_scores": {metric: score for metric in METRICS},
        },
        "special_reports": {
            "tool": {"total_count": 7, "passed_count": 7},
            "fora_de_escopo": {"total_count": 4, "passed_count": special_passed},
            "sem_resposta": {"total_count": 5, "passed_count": 5},
        },
    }


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_summary_schema_rejects_bool_duplicate_ids_and_invalid_counts(tmp_path: Path) -> None:
    summary = _summary(run_id="candidate")
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")
    assert load_evaluation_summary(path) == summary

    summary["rag_respondible"]["aggregate_scores"]["faithfulness"] = True
    path.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="faithfulness"):
        load_evaluation_summary(path)

    summary = _summary(run_id="candidate")
    summary["rag_respondible"]["subquestion_ids"].append(RAG_IDS[0])
    path.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicado"):
        load_evaluation_summary(path)

    summary = _summary(run_id="candidate")
    summary["special_reports"]["tool"] = {"total_count": 7, "passed_count": 8}
    path.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="tool"):
        load_evaluation_summary(path)


def test_gate_fails_on_metric_regression_and_reports_exact_delta() -> None:
    baseline = _summary(run_id="baseline", score=0.8)
    candidate = _summary(run_id="candidate", score=0.8)
    candidate["rag_respondible"]["aggregate_scores"]["faithfulness"] = 0.79

    report = compare_evaluations(baseline, candidate, _policy())

    assert report["decision"] == "fail"
    assert report["metric_comparison"]["faithfulness"] == {
        "baseline": 0.8,
        "candidate": 0.79,
        "delta": pytest.approx(-0.01),
        "max_allowed_drop": 0.0,
        "passed": False,
    }
    assert report["reasons"] == ["metric_regression:faithfulness"]


def test_gate_passes_improvement_with_identical_provenance_and_recorte() -> None:
    baseline = _summary(run_id="baseline", score=0.8)
    candidate = _summary(run_id="candidate", score=0.81)

    report = compare_evaluations(baseline, candidate, _policy())

    assert report["decision"] == "pass"
    assert report["reasons"] == []
    assert all(item["passed"] for item in report["metric_comparison"].values())
    assert all(item["passed"] for item in report["special_comparison"].values())
    assert report["provenance"] == {
        "dataset_git_blob_sha1": "1" * 40,
        "manifest_git_blob_sha1": "2" * 40,
        "slice_contract_git_blob_sha1": "3" * 40,
        "taxonomy_version": "1.0.0",
        "score_mechanism": "deterministic_fixture",
        "rag_subquestion_ids": RAG_IDS,
    }


@pytest.mark.parametrize(
    ("field", "candidate_value"),
    [
        ("dataset_git_blob_sha1", "4" * 40),
        ("manifest_git_blob_sha1", "5" * 40),
        ("slice_contract_git_blob_sha1", "6" * 40),
        ("taxonomy_version", "2.0.0"),
        ("score_mechanism", "different_mechanism"),
    ],
)
def test_gate_rejects_non_comparable_inputs(field: str, candidate_value: str) -> None:
    baseline = _summary(run_id="baseline")
    candidate = _summary(run_id="candidate")
    candidate[field] = candidate_value

    with pytest.raises(ValueError, match=field):
        compare_evaluations(baseline, candidate, _policy())


def test_gate_rejects_different_or_reordered_rag_recorte() -> None:
    baseline = _summary(run_id="baseline")
    candidate = _summary(run_id="candidate")
    candidate["rag_respondible"]["subquestion_ids"] = list(reversed(RAG_IDS))

    with pytest.raises(ValueError, match="rag_subquestion_ids"):
        compare_evaluations(baseline, candidate, _policy())


def test_special_category_regression_fails_without_entering_rag_scores() -> None:
    baseline = _summary(run_id="baseline")
    candidate = _summary(run_id="candidate", special_passed=3)

    report = compare_evaluations(baseline, candidate, _policy())

    assert report["decision"] == "fail"
    assert report["reasons"] == ["special_regression:fora_de_escopo"]
    assert report["special_comparison"]["fora_de_escopo"]["new_failures"] == 1
    assert set(report["metric_comparison"]) == METRICS


def test_versioned_self_test_fixtures_generate_passing_ci_evidence() -> None:
    baseline = load_evaluation_summary(FIXTURE_DIR / "baseline.json")
    candidate = load_evaluation_summary(FIXTURE_DIR / "candidate.json")
    contract_path = ROOT / "src" / "evaluation" / "recortes_avaliacao_v1.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    expected_rag_ids = [
        subquestion["id"]
        for case in contract["cases"]
        for subquestion in case["subquestions"]
        if subquestion["requires_retrieval"]
    ]

    report = compare_evaluations(baseline, candidate, _policy())

    assert baseline["dataset_git_blob_sha1"] == canonical_git_blob_sha1(
        ROOT / "src" / "evaluation" / "dataset.jsonl"
    )
    assert baseline["manifest_git_blob_sha1"] == canonical_git_blob_sha1(
        ROOT / "knowledge_base" / "manifest.json"
    )
    assert baseline["slice_contract_git_blob_sha1"] == canonical_git_blob_sha1(contract_path)
    assert baseline["rag_respondible"]["subquestion_ids"] == expected_rag_ids
    assert report["schema_version"] == "1.0.0"
    assert report["evidence_kind"] == "gate_self_test"
    assert report["decision"] == "pass"
    assert report["baseline_run_id"] == "regression-fixture-baseline-v1"
    assert report["candidate_run_id"] == "regression-fixture-candidate-v1"
