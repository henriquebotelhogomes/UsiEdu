"""Contrato e agregador dos recortes de avaliação da T02.3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.evaluation.slices import aggregate_results, describe_slices, load_contract

ROOT = Path(__file__).parent.parent.parent
CONTRACT_PATH = ROOT / "src" / "evaluation" / "recortes_avaliacao_v1.json"
DATASET_PATH = ROOT / "src" / "evaluation" / "dataset.jsonl"
EVIDENCE_PATH = ROOT / "src" / "evaluation" / "evidencia_recortes_t02_3.json"
METRICS = {
    "faithfulness",
    "context_precision",
    "context_recall",
    "answer_relevancy",
}
CATEGORIES = {
    "direct",
    "tool",
    "composta",
    "fora_de_escopo",
    "sem_resposta",
}
ASSERTIONS = {
    "direct": METRICS,
    "tool": {
        "value_correct",
        "authorization_respected",
        "retrieval_calls_zero",
    },
    "fora_de_escopo": {
        "redirected_to_usiedu_scope",
        "rag_calls_zero",
        "agent_calls_zero",
    },
    "sem_resposta": {
        "honest_refusal",
        "fabricated_sources_zero",
    },
}


def _dataset() -> list[dict]:
    return [
        json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines() if line
    ]


def _passing_results(contract: dict, score: float = 0.8) -> list[dict]:
    results = []
    for case in contract["cases"]:
        for subquestion in case["subquestions"]:
            category = subquestion["category"]
            results.append(
                {
                    "case_id": case["id"],
                    "subquestion_id": subquestion["id"],
                    "metrics": (
                        {metric: score for metric in METRICS}
                        if subquestion["requires_retrieval"]
                        else None
                    ),
                    "assertions": (
                        {}
                        if subquestion["requires_retrieval"]
                        else {name: True for name in ASSERTIONS[category]}
                    ),
                }
            )
    return results


def test_contract_schema_covers_dataset_without_duplicate_ids() -> None:
    contract = load_contract(CONTRACT_PATH)
    dataset = _dataset()
    dataset_by_id = {case["id"]: case for case in dataset}
    case_ids = [case["id"] for case in contract["cases"]]
    subquestion_ids = [
        subquestion["id"] for case in contract["cases"] for subquestion in case["subquestions"]
    ]

    assert contract["schema_version"] == "1.0.0"
    assert contract["taxonomy_version"] == "1.0.0"
    assert set(contract) == {
        "schema_version",
        "taxonomy_version",
        "aggregation",
        "cases",
    }
    assert len(case_ids) == len(set(case_ids))
    assert set(case_ids) == set(dataset_by_id) == {f"q{number:03d}" for number in range(1, 31)}
    assert len(subquestion_ids) == len(set(subquestion_ids)) == 33

    for case in contract["cases"]:
        assert set(case) == {"id", "category", "subquestions"}
        assert case["category"] == dataset_by_id[case["id"]]["category"]
        assert case["category"] in CATEGORIES
        assert isinstance(case["subquestions"], list) and case["subquestions"]
        for subquestion in case["subquestions"]:
            assert set(subquestion) == {
                "id",
                "category",
                "requires_retrieval",
                "expectation",
                "assertions",
            }
            assert subquestion["category"] in CATEGORIES - {"composta"}
            assert isinstance(subquestion["requires_retrieval"], bool)
            assert isinstance(subquestion["expectation"], str) and subquestion["expectation"]
            assert set(subquestion["assertions"]) == ASSERTIONS[subquestion["category"]]
            assert subquestion["requires_retrieval"] is (subquestion["category"] == "direct")


def test_composed_cases_have_ordered_explicit_subquestions() -> None:
    cases = {case["id"]: case for case in load_contract(CONTRACT_PATH)["cases"]}

    assert [
        (sub["id"], sub["category"], sub["requires_retrieval"])
        for sub in cases["q008"]["subquestions"]
    ] == [
        ("q008.notas", "tool", False),
        ("q008.boleto", "tool", False),
    ]
    assert [
        (sub["id"], sub["category"], sub["requires_retrieval"])
        for sub in cases["q023"]["subquestions"]
    ] == [
        ("q023.teletrabalho", "direct", True),
        ("q023.boleto", "tool", False),
    ]
    assert [
        (sub["id"], sub["category"], sub["requires_retrieval"])
        for sub in cases["q030"]["subquestions"]
    ] == [
        ("q030.seguranca", "direct", True),
        ("q030.treinamentos", "direct", True),
    ]


def test_aggregator_builds_each_report_and_only_retrieval_enters_rag() -> None:
    contract = load_contract(CONTRACT_PATH)
    report = aggregate_results(contract, _passing_results(contract))

    assert report["rag_respondible"]["subquestion_count"] == 17
    assert set(report["rag_respondible"]["metrics"]) == METRICS
    assert report["rag_respondible"]["metrics"] == {
        metric: pytest.approx(0.8) for metric in METRICS
    }
    assert "q008.notas" not in report["rag_respondible"]["subquestion_ids"]
    assert "q008.boleto" not in report["rag_respondible"]["subquestion_ids"]
    assert "q023.teletrabalho" in report["rag_respondible"]["subquestion_ids"]
    assert "q023.boleto" not in report["rag_respondible"]["subquestion_ids"]
    assert {"q030.seguranca", "q030.treinamentos"} <= set(
        report["rag_respondible"]["subquestion_ids"]
    )

    assert report["tool"]["subquestion_count"] == 7
    assert report["tool"]["passed_count"] == 7
    assert report["fora_de_escopo"]["case_count"] == 4
    assert report["fora_de_escopo"]["passed_count"] == 4
    assert report["sem_resposta"]["case_count"] == 5
    assert report["sem_resposta"]["passed_count"] == 5
    assert set(report["composta"]) == {"q008", "q023", "q030"}
    assert report["composta"]["q008"]["rag_contribution_ids"] == []
    assert report["composta"]["q023"]["rag_contribution_ids"] == ["q023.teletrabalho"]
    assert report["composta"]["q030"]["rag_contribution_ids"] == [
        "q030.seguranca",
        "q030.treinamentos",
    ]


def test_aggregator_rejects_boolean_metric_duplicate_and_missing_result() -> None:
    contract = load_contract(CONTRACT_PATH)
    results = _passing_results(contract)
    results[0]["metrics"]["faithfulness"] = True
    with pytest.raises(ValueError, match="faithfulness"):
        aggregate_results(contract, results)

    results = _passing_results(contract)
    results.append(dict(results[0]))
    with pytest.raises(ValueError, match="duplicado"):
        aggregate_results(contract, results)

    with pytest.raises(ValueError, match="ausentes"):
        aggregate_results(contract, _passing_results(contract)[:-1])


def test_failed_deterministic_assertion_is_visible_outside_rag_aggregate() -> None:
    contract = load_contract(CONTRACT_PATH)
    results = _passing_results(contract)
    q004 = next(result for result in results if result["subquestion_id"] == "q004.tool")
    q004["assertions"]["authorization_respected"] = False

    report = aggregate_results(contract, results)

    assert report["tool"]["passed_count"] == 6
    failed = next(item for item in report["tool"]["items"] if item["subquestion_id"] == "q004.tool")
    assert failed["passed"] is False
    assert report["rag_respondible"]["metrics"] == {
        metric: pytest.approx(0.8) for metric in METRICS
    }


def test_redirect_and_refusal_failures_stay_in_their_own_reports() -> None:
    contract = load_contract(CONTRACT_PATH)
    results = _passing_results(contract)
    q009 = next(result for result in results if result["subquestion_id"] == "q009.redirect")
    q009["assertions"]["rag_calls_zero"] = False
    q022 = next(result for result in results if result["subquestion_id"] == "q022.refusal")
    q022["assertions"]["fabricated_sources_zero"] = False

    report = aggregate_results(contract, results)

    assert report["fora_de_escopo"]["passed_count"] == 3
    assert report["sem_resposta"]["passed_count"] == 4
    assert report["rag_respondible"]["metrics"] == {
        metric: pytest.approx(0.8) for metric in METRICS
    }


def test_structural_evidence_matches_contract_without_fabricated_scores() -> None:
    contract = load_contract(CONTRACT_PATH)
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    assert evidence == describe_slices(contract)
    assert evidence["score_status"] == "not_recomputed_in_t02_3"
    assert evidence["counts"] == {
        "cases": 30,
        "subquestions": 33,
        "rag_respondible": 17,
        "tool": 7,
        "fora_de_escopo": 4,
        "sem_resposta": 5,
        "composta": 3,
    }


def test_documentation_marks_only_t02_3_complete() -> None:
    document = (ROOT / "docs" / "profissionalizacao" / "02-qualidade-rag.md").read_text(
        encoding="utf-8"
    )

    assert "T02.2 parcial; T02.3 concluída; T02.4–T02.5 não iniciadas" in document
    assert "- [x] **T02.3 — Definir recortes" in document
    assert "`src/evaluation/recortes_avaliacao_v1.json`" in document
    assert "`src/evaluation/evidencia_recortes_t02_3.json`" in document
    assert "- [ ] **T02.4 — Criar regressão automatizada**" in document
