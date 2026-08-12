"""Gate determinístico de regressão dos recortes de avaliação RAG."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

METRICS = (
    "faithfulness",
    "context_precision",
    "context_recall",
    "answer_relevancy",
)
SPECIAL_CATEGORIES = ("tool", "fora_de_escopo", "sem_resposta")
SUMMARY_FIELDS = {
    "schema_version",
    "evidence_kind",
    "run_id",
    "dataset_git_blob_sha1",
    "manifest_git_blob_sha1",
    "slice_contract_git_blob_sha1",
    "taxonomy_version",
    "score_mechanism",
    "rag_respondible",
    "special_reports",
}
COMPARABILITY_FIELDS = (
    "dataset_git_blob_sha1",
    "manifest_git_blob_sha1",
    "slice_contract_git_blob_sha1",
    "taxonomy_version",
    "score_mechanism",
)
_GIT_SHA1 = re.compile(r"^[0-9a-f]{40}$")


def _is_score(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and 0 <= value <= 1


def validate_evaluation_summary(summary: dict[str, Any]) -> None:
    """Valida proveniência, recorte, scores e relatórios determinísticos."""
    if set(summary) != SUMMARY_FIELDS:
        raise ValueError("campos do resumo invalidos")
    if summary["schema_version"] != "1.0.0":
        raise ValueError("schema_version deve ser 1.0.0")
    if summary["evidence_kind"] not in {"evaluation_run", "gate_self_test"}:
        raise ValueError("evidence_kind invalido")
    for field in ("run_id", "taxonomy_version", "score_mechanism"):
        if not isinstance(summary[field], str) or not summary[field]:
            raise ValueError(f"{field} invalido")
    for field in (
        "dataset_git_blob_sha1",
        "manifest_git_blob_sha1",
        "slice_contract_git_blob_sha1",
    ):
        if not isinstance(summary[field], str) or not _GIT_SHA1.fullmatch(summary[field]):
            raise ValueError(f"{field} invalido")

    rag = summary["rag_respondible"]
    if not isinstance(rag, dict) or set(rag) != {"subquestion_ids", "aggregate_scores"}:
        raise ValueError("rag_respondible invalido")
    subquestion_ids = rag["subquestion_ids"]
    if (
        not isinstance(subquestion_ids, list)
        or not subquestion_ids
        or not all(isinstance(item, str) and item for item in subquestion_ids)
    ):
        raise ValueError("rag_subquestion_ids invalidos")
    if len(subquestion_ids) != len(set(subquestion_ids)):
        raise ValueError("rag_subquestion_id duplicado")
    scores = rag["aggregate_scores"]
    if not isinstance(scores, dict) or set(scores) != set(METRICS):
        raise ValueError("aggregate_scores invalidos")
    for metric, score in scores.items():
        if not _is_score(score):
            raise ValueError(f"{metric} invalida")

    special = summary["special_reports"]
    if not isinstance(special, dict) or set(special) != set(SPECIAL_CATEGORIES):
        raise ValueError("special_reports invalidos")
    for category, item in special.items():
        if not isinstance(item, dict) or set(item) != {"total_count", "passed_count"}:
            raise ValueError(f"{category} invalido")
        total = item["total_count"]
        passed = item["passed_count"]
        if (
            not isinstance(total, int)
            or isinstance(total, bool)
            or not isinstance(passed, int)
            or isinstance(passed, bool)
            or total < 0
            or passed < 0
            or passed > total
        ):
            raise ValueError(f"{category} possui contagens invalidas")


def load_evaluation_summary(path: Path) -> dict[str, Any]:
    """Carrega um resumo autocontido e rejeita artefatos adulterados."""
    summary = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict):
        raise ValueError("resumo deve ser objeto JSON")
    validate_evaluation_summary(summary)
    return summary


def validate_policy(policy: dict[str, Any]) -> None:
    """Valida a política versionada usada para decidir regressões."""
    if set(policy) != {
        "schema_version",
        "policy_id",
        "metric_max_allowed_drop",
        "special_max_new_failures",
    }:
        raise ValueError("campos da politica invalidos")
    if policy["schema_version"] != "1.0.0":
        raise ValueError("schema_version da politica invalido")
    if not isinstance(policy["policy_id"], str) or not policy["policy_id"]:
        raise ValueError("policy_id invalido")
    metric_limits = policy["metric_max_allowed_drop"]
    if not isinstance(metric_limits, dict) or set(metric_limits) != set(METRICS):
        raise ValueError("limites de metricas invalidos")
    for metric, limit in metric_limits.items():
        if not _is_score(limit):
            raise ValueError(f"limite invalido para {metric}")
    special_limits = policy["special_max_new_failures"]
    if not isinstance(special_limits, dict) or set(special_limits) != set(SPECIAL_CATEGORIES):
        raise ValueError("limites especiais invalidos")
    for category, limit in special_limits.items():
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError(f"limite invalido para {category}")


def compare_evaluations(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Compara artefatos equivalentes e retorna decisão reproduzível."""
    validate_evaluation_summary(baseline)
    validate_evaluation_summary(candidate)
    validate_policy(policy)
    if baseline["evidence_kind"] != candidate["evidence_kind"]:
        raise ValueError("evidence_kind diverge entre baseline e candidato")
    for field in COMPARABILITY_FIELDS:
        if baseline[field] != candidate[field]:
            raise ValueError(f"{field} diverge entre baseline e candidato")

    baseline_ids = baseline["rag_respondible"]["subquestion_ids"]
    candidate_ids = candidate["rag_respondible"]["subquestion_ids"]
    if baseline_ids != candidate_ids:
        raise ValueError("rag_subquestion_ids divergem entre baseline e candidato")

    reasons: list[str] = []
    metric_comparison = {}
    for metric in METRICS:
        baseline_score = baseline["rag_respondible"]["aggregate_scores"][metric]
        candidate_score = candidate["rag_respondible"]["aggregate_scores"][metric]
        delta = candidate_score - baseline_score
        max_drop = policy["metric_max_allowed_drop"][metric]
        passed = delta >= -max_drop
        metric_comparison[metric] = {
            "baseline": baseline_score,
            "candidate": candidate_score,
            "delta": delta,
            "max_allowed_drop": max_drop,
            "passed": passed,
        }
        if not passed:
            reasons.append(f"metric_regression:{metric}")

    special_comparison = {}
    for category in SPECIAL_CATEGORIES:
        baseline_item = baseline["special_reports"][category]
        candidate_item = candidate["special_reports"][category]
        if baseline_item["total_count"] != candidate_item["total_count"]:
            raise ValueError(f"total_count diverge para {category}")
        baseline_failures = baseline_item["total_count"] - baseline_item["passed_count"]
        candidate_failures = candidate_item["total_count"] - candidate_item["passed_count"]
        new_failures = candidate_failures - baseline_failures
        max_new_failures = policy["special_max_new_failures"][category]
        passed = new_failures <= max_new_failures
        special_comparison[category] = {
            "total_count": baseline_item["total_count"],
            "baseline_passed": baseline_item["passed_count"],
            "candidate_passed": candidate_item["passed_count"],
            "new_failures": new_failures,
            "max_new_failures": max_new_failures,
            "passed": passed,
        }
        if not passed:
            reasons.append(f"special_regression:{category}")

    return {
        "schema_version": "1.0.0",
        "evidence_kind": baseline["evidence_kind"],
        "policy_id": policy["policy_id"],
        "baseline_run_id": baseline["run_id"],
        "candidate_run_id": candidate["run_id"],
        "provenance": {
            field: baseline[field]
            for field in (
                "dataset_git_blob_sha1",
                "manifest_git_blob_sha1",
                "slice_contract_git_blob_sha1",
                "taxonomy_version",
                "score_mechanism",
            )
        }
        | {"rag_subquestion_ids": baseline_ids},
        "metric_comparison": metric_comparison,
        "special_comparison": special_comparison,
        "decision": "pass" if not reasons else "fail",
        "reasons": reasons,
    }


def main() -> None:
    """Executa o gate e sempre publica a evidência antes de sinalizar falha."""
    parser = argparse.ArgumentParser(description="Compara baseline e candidato RAG")
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    baseline = load_evaluation_summary(args.baseline)
    candidate = load_evaluation_summary(args.candidate)
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    report = compare_evaluations(baseline, candidate, policy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Decisao do gate: {report['decision']}; evidencia: {args.output}")
    if report["decision"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
