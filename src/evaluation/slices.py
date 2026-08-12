"""Contrato e agregação dos recortes de avaliação da T02.3."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

METRICS = (
    "faithfulness",
    "context_precision",
    "context_recall",
    "answer_relevancy",
)
CATEGORIES = {
    "direct",
    "tool",
    "composta",
    "fora_de_escopo",
    "sem_resposta",
}
ASSERTIONS = {
    "direct": set(METRICS),
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


def _is_score(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and 0 <= value <= 1


def load_contract(path: Path) -> dict[str, Any]:
    """Carrega e valida o contrato versionado dos recortes."""
    contract = json.loads(path.read_text(encoding="utf-8"))
    validate_contract(contract)
    return contract


def validate_contract(contract: dict[str, Any]) -> None:
    """Rejeita contrato incompleto, duplicado ou incoerente."""
    if set(contract) != {"schema_version", "taxonomy_version", "aggregation", "cases"}:
        raise ValueError("campos do contrato invalidos")
    if contract["schema_version"] != "1.0.0" or contract["taxonomy_version"] != "1.0.0":
        raise ValueError("versao do contrato invalida")
    if contract["aggregation"] != {
        "rag_respondible": {
            "selector": "requires_retrieval=true",
            "method": "simple_mean_per_metric",
        },
        "tool": {"selector": "category=tool", "method": "deterministic_assertions"},
        "composta": {"selector": "category=composta", "method": "subquestion_report"},
        "fora_de_escopo": {
            "selector": "category=fora_de_escopo",
            "method": "deterministic_assertions",
        },
        "sem_resposta": {
            "selector": "category=sem_resposta",
            "method": "deterministic_assertions",
        },
    }:
        raise ValueError("regras de agregacao invalidas")

    cases = contract["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases deve ser lista nao vazia")
    case_ids = [case.get("id") for case in cases]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"case_id duplicado: {', '.join(duplicates)}")

    all_subquestion_ids: list[str] = []
    for case in cases:
        if set(case) != {"id", "category", "subquestions"}:
            raise ValueError(f"campos invalidos no caso {case.get('id')}")
        if case["category"] not in CATEGORIES:
            raise ValueError(f"categoria invalida no caso {case['id']}")
        subquestions = case["subquestions"]
        if not isinstance(subquestions, list) or not subquestions:
            raise ValueError(f"subquestions ausentes no caso {case['id']}")
        if case["category"] != "composta" and len(subquestions) != 1:
            raise ValueError(f"caso nao composto deve ter uma subpergunta: {case['id']}")
        for subquestion in subquestions:
            if set(subquestion) != {
                "id",
                "category",
                "requires_retrieval",
                "expectation",
                "assertions",
            }:
                raise ValueError(f"campos invalidos na subpergunta de {case['id']}")
            category = subquestion["category"]
            if category not in ASSERTIONS:
                raise ValueError(f"categoria invalida na subpergunta {subquestion['id']}")
            if not isinstance(subquestion["requires_retrieval"], bool):
                raise ValueError(f"requires_retrieval invalido em {subquestion['id']}")
            if subquestion["requires_retrieval"] != (category == "direct"):
                raise ValueError(f"recuperacao incoerente em {subquestion['id']}")
            if not isinstance(subquestion["expectation"], str) or not subquestion["expectation"]:
                raise ValueError(f"expectation invalida em {subquestion['id']}")
            if set(subquestion["assertions"]) != ASSERTIONS[category]:
                raise ValueError(f"assertions invalidas em {subquestion['id']}")
            all_subquestion_ids.append(subquestion["id"])
    duplicates = sorted(
        {
            subquestion_id
            for subquestion_id in all_subquestion_ids
            if all_subquestion_ids.count(subquestion_id) > 1
        }
    )
    if duplicates:
        raise ValueError(f"subquestion_id duplicado: {', '.join(duplicates)}")


def _expected_subquestions(
    contract: dict[str, Any],
) -> dict[str, tuple[dict[str, Any], dict[str, Any]]]:
    return {
        subquestion["id"]: (case, subquestion)
        for case in contract["cases"]
        for subquestion in case["subquestions"]
    }


def _validate_results(
    contract: dict[str, Any], results: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    expected = _expected_subquestions(contract)
    result_ids = [result.get("subquestion_id") for result in results]
    duplicates = sorted({result_id for result_id in result_ids if result_ids.count(result_id) > 1})
    if duplicates:
        raise ValueError(f"resultado duplicado: {', '.join(duplicates)}")
    missing = sorted(set(expected) - set(result_ids))
    extra = sorted(set(result_ids) - set(expected))
    if missing or extra:
        raise ValueError(f"resultados ausentes={missing}; extras={extra}")

    by_id = {result["subquestion_id"]: result for result in results}
    for subquestion_id, result in by_id.items():
        if set(result) != {"case_id", "subquestion_id", "metrics", "assertions"}:
            raise ValueError(f"campos invalidos no resultado {subquestion_id}")
        case, subquestion = expected[subquestion_id]
        if result["case_id"] != case["id"]:
            raise ValueError(f"case_id incoerente em {subquestion_id}")
        if subquestion["requires_retrieval"]:
            metrics = result["metrics"]
            if not isinstance(metrics, dict) or set(metrics) != set(METRICS):
                raise ValueError(f"metrics invalidas em {subquestion_id}")
            for metric, value in metrics.items():
                if not _is_score(value):
                    raise ValueError(f"{metric} invalida em {subquestion_id}")
            if result["assertions"] != {}:
                raise ValueError(f"assertions indevidas em {subquestion_id}")
        else:
            if result["metrics"] is not None:
                raise ValueError(f"metrics indevidas em {subquestion_id}")
            assertions = result["assertions"]
            if not isinstance(assertions, dict) or set(assertions) != set(
                subquestion["assertions"]
            ):
                raise ValueError(f"assertions invalidas em {subquestion_id}")
            if not all(isinstance(value, bool) for value in assertions.values()):
                raise ValueError(f"assertions devem ser booleanas em {subquestion_id}")
    return by_id


def _deterministic_report(
    contract: dict[str, Any],
    results: dict[str, dict[str, Any]],
    category: str,
    *,
    count_name: str,
) -> dict[str, Any]:
    expected = _expected_subquestions(contract)
    items = []
    for subquestion_id, (_, subquestion) in expected.items():
        if subquestion["category"] != category:
            continue
        result = results[subquestion_id]
        items.append(
            {
                "case_id": result["case_id"],
                "subquestion_id": subquestion_id,
                "assertions": result["assertions"],
                "passed": all(result["assertions"].values()),
            }
        )
    return {
        count_name: len(items),
        "passed_count": sum(item["passed"] for item in items),
        "items": items,
    }


def aggregate_results(contract: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    """Agrega métricas RAG e relatórios determinísticos sem misturar recortes."""
    validate_contract(contract)
    by_id = _validate_results(contract, results)
    expected = _expected_subquestions(contract)
    rag_ids = [
        subquestion_id
        for subquestion_id, (_, subquestion) in expected.items()
        if subquestion["requires_retrieval"]
    ]
    rag_metrics = {
        metric: sum(by_id[subquestion_id]["metrics"][metric] for subquestion_id in rag_ids)
        / len(rag_ids)
        for metric in METRICS
    }

    composed = {}
    for case in contract["cases"]:
        if case["category"] != "composta":
            continue
        composed[case["id"]] = {
            "subquestions": [
                {
                    "subquestion_id": subquestion["id"],
                    "category": subquestion["category"],
                    "requires_retrieval": subquestion["requires_retrieval"],
                    "result": by_id[subquestion["id"]],
                }
                for subquestion in case["subquestions"]
            ],
            "rag_contribution_ids": [
                subquestion["id"]
                for subquestion in case["subquestions"]
                if subquestion["requires_retrieval"]
            ],
        }

    return {
        "rag_respondible": {
            "subquestion_count": len(rag_ids),
            "subquestion_ids": rag_ids,
            "metrics": rag_metrics,
        },
        "tool": _deterministic_report(contract, by_id, "tool", count_name="subquestion_count"),
        "fora_de_escopo": _deterministic_report(
            contract, by_id, "fora_de_escopo", count_name="case_count"
        ),
        "sem_resposta": _deterministic_report(
            contract, by_id, "sem_resposta", count_name="case_count"
        ),
        "composta": composed,
    }


def describe_slices(contract: dict[str, Any]) -> dict[str, Any]:
    """Publica a composição estrutural dos recortes sem fabricar scores."""
    validate_contract(contract)
    expected = _expected_subquestions(contract)
    rag_ids = [
        subquestion_id
        for subquestion_id, (_, subquestion) in expected.items()
        if subquestion["requires_retrieval"]
    ]
    tool_ids = [
        subquestion_id
        for subquestion_id, (_, subquestion) in expected.items()
        if subquestion["category"] == "tool"
    ]
    outside_ids = [case["id"] for case in contract["cases"] if case["category"] == "fora_de_escopo"]
    no_answer_ids = [case["id"] for case in contract["cases"] if case["category"] == "sem_resposta"]
    composed = {
        case["id"]: {
            "subquestion_ids": [subquestion["id"] for subquestion in case["subquestions"]],
            "rag_contribution_ids": [
                subquestion["id"]
                for subquestion in case["subquestions"]
                if subquestion["requires_retrieval"]
            ],
        }
        for case in contract["cases"]
        if case["category"] == "composta"
    }
    return {
        "schema_version": "1.0.0",
        "taxonomy_version": contract["taxonomy_version"],
        "score_status": "not_recomputed_in_t02_3",
        "counts": {
            "cases": len(contract["cases"]),
            "subquestions": len(expected),
            "rag_respondible": len(rag_ids),
            "tool": len(tool_ids),
            "fora_de_escopo": len(outside_ids),
            "sem_resposta": len(no_answer_ids),
            "composta": len(composed),
        },
        "slices": {
            "rag_respondible": rag_ids,
            "tool": tool_ids,
            "fora_de_escopo": outside_ids,
            "sem_resposta": no_answer_ids,
            "composta": composed,
        },
    }


def main() -> None:
    """Gera evidência estrutural dos recortes sem executar ou pontuar casos."""
    parser = argparse.ArgumentParser(description="Gera evidencia dos recortes da T02.3")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = describe_slices(load_contract(args.contract))
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Evidencia gerada em: {args.output}")


if __name__ == "__main__":
    main()
