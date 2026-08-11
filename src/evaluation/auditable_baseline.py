"""Execução auditável e reprodutível do baseline RAG da T02.1b."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import HumanMessage

from src.evaluation.run_ragas import _avaliar_resposta, _carregar_grafo, _extrair_resposta

METRIC_NAMES = (
    "faithfulness",
    "context_precision",
    "context_recall",
    "answer_relevancy",
)
RECORD_FIELDS = {
    "schema_version",
    "run_id",
    "case_id",
    "profile",
    "category",
    "question",
    "reference_answer",
    "started_at",
    "duration_ms",
    "status",
    "answer",
    "sources",
    "delegations",
    "error",
    "usage",
    "estimated_cost_usd",
    "scores",
    "score_mechanism",
}
VALID_CATEGORIES = {
    "direct",
    "tool",
    "composta",
    "fora_de_escopo",
    "sem_resposta",
}


class BudgetExceededError(RuntimeError):
    """A execução excederia ou excedeu o teto financeiro configurado."""


def _is_number(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def canonical_bytes(path: Path) -> bytes:
    """Retorna bytes com LF canônico para hashes independentes do checkout."""
    return path.read_bytes().replace(b"\r\n", b"\n")


def canonical_git_blob_sha1(path: Path) -> str:
    """Calcula o Git blob ID SHA-1 sobre bytes com LF canônico."""
    content = canonical_bytes(path)
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content, usedforsecurity=False).hexdigest()


def canonical_sha256(path: Path) -> str:
    """Calcula SHA-256 sobre bytes com LF canônico."""
    return hashlib.sha256(canonical_bytes(path)).hexdigest()


def validate_run_record(record: dict[str, Any]) -> None:
    """Valida o contrato estrutural de um registro por caso."""
    if set(record) != RECORD_FIELDS:
        missing = sorted(RECORD_FIELDS - set(record))
        extra = sorted(set(record) - RECORD_FIELDS)
        raise ValueError(f"campos invalidos; ausentes={missing}; extras={extra}")
    if record["schema_version"] != "1.0.0":
        raise ValueError("schema_version deve ser 1.0.0")
    if not isinstance(record["run_id"], str) or not record["run_id"]:
        raise ValueError("run_id invalido")
    if not isinstance(record["case_id"], str) or not record["case_id"].startswith("q"):
        raise ValueError("case_id invalido")
    if record["profile"] not in {"student", "staff"}:
        raise ValueError("profile invalido")
    if record["category"] not in VALID_CATEGORIES:
        raise ValueError("category invalida")
    for field in ("question", "reference_answer", "started_at", "score_mechanism"):
        if not isinstance(record[field], str) or not record[field]:
            raise ValueError(f"{field} invalido")
    if not _is_number(record["duration_ms"]) or record["duration_ms"] < 0:
        raise ValueError("duration_ms invalido")
    if record["status"] not in {"success", "error"}:
        raise ValueError("status invalido")
    if not isinstance(record["sources"], list):
        raise ValueError("sources invalido")
    if not isinstance(record["delegations"], list) or not all(
        isinstance(agent, str) and agent for agent in record["delegations"]
    ):
        raise ValueError("delegations invalido")
    if not _is_number(record["estimated_cost_usd"]) or record["estimated_cost_usd"] < 0:
        raise ValueError("estimated_cost_usd invalido")

    usage = record["usage"]
    if not isinstance(usage, dict) or set(usage) != {
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "by_model",
    }:
        raise ValueError("usage invalido")
    for field in ("input_tokens", "output_tokens", "total_tokens"):
        if not isinstance(usage[field], int) or isinstance(usage[field], bool) or usage[field] < 0:
            raise ValueError(f"{field} invalido")
    if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
        raise ValueError("total_tokens incoerente")
    if not isinstance(usage["by_model"], dict):
        raise ValueError("by_model invalido")
    for model, model_usage in usage["by_model"].items():
        if not isinstance(model, str) or not model or not isinstance(model_usage, dict):
            raise ValueError("uso por modelo invalido")
        for field in ("input_tokens", "output_tokens", "total_tokens"):
            value = model_usage.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{field} invalido para {model}")
        if model_usage["total_tokens"] != (
            model_usage["input_tokens"] + model_usage["output_tokens"]
        ):
            raise ValueError(f"total_tokens incoerente para {model}")

    scores = record["scores"]
    if not isinstance(scores, dict) or set(scores) != set(METRIC_NAMES):
        raise ValueError("scores invalidos")
    for metric, score in scores.items():
        if score is not None and (not _is_number(score) or not 0 <= score <= 1):
            raise ValueError(f"{metric} invalido")

    if record["status"] == "success":
        if not isinstance(record["answer"], str):
            raise ValueError("answer invalida para sucesso")
        if record["error"] is not None:
            raise ValueError("error deve ser nulo para sucesso")
        if any(score is None for score in scores.values()):
            raise ValueError("scores devem existir para sucesso")
    else:
        if record["answer"] is not None:
            raise ValueError("answer deve ser nula para erro")
        error = record["error"]
        if (
            not isinstance(error, dict)
            or set(error) != {"type", "message"}
            or not all(isinstance(value, str) and value for value in error.values())
        ):
            raise ValueError("error deve preservar tipo e mensagem")
        if any(score is not None for score in scores.values()):
            raise ValueError("scores devem ser nulos para erro")


def load_run_records(path: Path) -> list[dict[str, Any]]:
    """Carrega JSONL, valida cada registro e rejeita IDs duplicados."""
    records = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    case_ids = [record.get("case_id") for record in records]
    duplicates = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"case_id duplicado: {', '.join(duplicates)}")
    for record in records:
        validate_run_record(record)
    return records


def compute_aggregate_scores(records: list[dict[str, Any]]) -> dict[str, float]:
    """Deriva médias somente de casos concluídos com score observável."""
    successful = [record for record in records if record["status"] == "success"]
    if not successful:
        return {metric: 0.0 for metric in METRIC_NAMES}
    return {
        metric: round(
            sum(record["scores"][metric] for record in successful) / len(successful),
            12,
        )
        for metric in METRIC_NAMES
    }


def estimate_cost_usd(
    usage: dict[str, Any],
    rates: dict[str, dict[str, float]],
    *,
    budget_usd: float,
) -> float:
    """Estima custo equivalente por tokens e rejeita valor acima do teto."""
    total = 0.0
    for model, model_usage in usage["by_model"].items():
        if model not in rates:
            raise ValueError(f"tarifa ausente para modelo {model}")
        rate = rates[model]
        total += (
            model_usage["input_tokens"] * rate["input_per_million_usd"]
            + model_usage["output_tokens"] * rate["output_per_million_usd"]
        ) / 1_000_000
    if total > budget_usd:
        raise BudgetExceededError(f"custo estimado US${total:.6f} excede teto US${budget_usd:.2f}")
    return total


def _normalize_usage(raw: dict[str, Any]) -> dict[str, Any]:
    by_model: dict[str, dict[str, int]] = {}
    for model, usage in raw.items():
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        by_model[model] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
    return {
        "input_tokens": sum(value["input_tokens"] for value in by_model.values()),
        "output_tokens": sum(value["output_tokens"] for value in by_model.values()),
        "total_tokens": sum(value["total_tokens"] for value in by_model.values()),
        "by_model": by_model,
    }


def _serialize_sources(result: dict[str, Any]) -> list[dict[str, Any]]:
    sources = []
    for source in result.get("retrieved_sources", []):
        if hasattr(source, "model_dump"):
            sources.append(source.model_dump(mode="json"))
        elif isinstance(source, dict):
            sources.append(source)
        else:
            raise TypeError(f"fonte nao serializavel: {type(source).__name__}")
    return sources


def _git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _initial_state(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "user_id": case["user_id"],
        "profile": case["profile"],
        "messages": [HumanMessage(content=case["question"])],
        "plan": None,
        "delegations": [],
        "agent_results": {},
        "retrieved_sources": [],
        "needs_more_info": False,
        "cycle_count": 0,
        "supervisor_decision": None,
    }


def _generate_report(
    records: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    diagnostics: dict[str, Any],
    source_commit: str,
    dataset_blob: str,
    manifest_blob: str,
    total_cost: float,
) -> str:
    aggregates = compute_aggregate_scores(records)
    by_category: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_category.setdefault(record["category"], []).append(record)

    lines = [
        "# Baseline auditável RAG — 2026-08-11",
        "",
        f"- Run ID: `{config['run_id']}`",
        f"- Commit da implementação/configuração: `{source_commit}`",
        f"- Dataset Git blob: `{dataset_blob}`",
        f"- Manifest Git blob: `{manifest_blob}`",
        (
            "- Modelos: router `deepseek-v4-flash`; agentes "
            "`deepseek-v4-pro`; temperatura `1.0`; máximo de saída `2048` tokens"
        ),
        f"- Mecanismo de score: `{config['scoring']['mechanism']}`",
        (
            f"- Custo equivalente estimado: **US$ {total_cost:.6f}** "
            f"(teto: US$ {config['budget']['total_usd']:.2f})"
        ),
        "",
        "> Este baseline preserva respostas, fontes, erros, duração e uso por caso. "
        "O mecanismo de score é a heurística legada e não executa métricas Ragas. "
        "Os valores abaixo não devem ser rotulados como avaliação Ragas real.",
        "",
        "## Resultado agregado legado",
        "",
        "| Métrica | Score |",
        "|---|---:|",
    ]
    for metric in METRIC_NAMES:
        lines.append(f"| {metric} | {aggregates[metric]:.6f} |")

    historical = {
        "faithfulness": 0.565,
        "context_precision": 0.645,
        "context_recall": 0.645,
        "answer_relevancy": 0.565,
    }
    lines += [
        "",
        "O agregado acima inclui todas as categorias apenas para comparação com o "
        "mecanismo legado. Ele não representa o futuro recorte RAG respondível.",
        "",
        "## Comparação descritiva com 06/08/2026",
        "",
        "| Métrica | Histórico | Novo auditável | Diferença |",
        "|---|---:|---:|---:|",
    ]
    for metric in METRIC_NAMES:
        lines.append(
            f"| {metric} | {historical[metric]:.6f} | {aggregates[metric]:.6f} | "
            f"{aggregates[metric] - historical[metric]:+.6f} |"
        )

    lines += [
        "",
        "A comparação é somente descritiva: o histórico não preservou saídas brutas e "
        "usou o dataset anterior à reclassificação de q022. A diferença não demonstra "
        "melhora ou regressão causal.",
        "",
        "## Sub-relatório por categoria",
        "",
        "| Categoria | Casos | Sucessos | Fontes | Faithfulness | Context precision | "
        "Context recall | Answer relevancy |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for category in sorted(by_category):
        category_records = by_category[category]
        category_scores = compute_aggregate_scores(category_records)
        lines.append(
            f"| {category} | {len(category_records)} | "
            f"{sum(record['status'] == 'success' for record in category_records)} | "
            f"{sum(len(record['sources']) for record in category_records)} | "
            f"{category_scores['faithfulness']:.6f} | "
            f"{category_scores['context_precision']:.6f} | "
            f"{category_scores['context_recall']:.6f} | "
            f"{category_scores['answer_relevancy']:.6f} |"
        )

    lines += [
        "",
        "## Casos",
        "",
        "| ID | Categoria | Status | Fontes | Duração (ms) | Tokens | Custo estimado (US$) "
        "| Faithfulness | Answer relevancy |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for record in records:
        faithfulness = record["scores"]["faithfulness"]
        relevancy = record["scores"]["answer_relevancy"]
        lines.append(
            f"| {record['case_id']} | {record['category']} | {record['status']} | "
            f"{len(record['sources'])} | {record['duration_ms']} | "
            f"{record['usage']['total_tokens']} | {record['estimated_cost_usd']:.8f} | "
            f"{'—' if faithfulness is None else f'{faithfulness:.6f}'} | "
            f"{'—' if relevancy is None else f'{relevancy:.6f}'} |"
        )

    lines += [
        "",
        "## Diagnóstico dos scores zero",
        "",
        "| ID | Métricas | Causa | Evidência |",
        "|---|---|---|---|",
    ]
    for case in diagnostics["cases"]:
        evidence = case["evidence"]
        lines.append(
            f"| {case['case_id']} | {', '.join(case['zero_metrics'])} | "
            f"{case['cause']} | resposta contém `{evidence['answer_contains']}`; "
            f"fontes={evidence['sources_count']}; "
            f"delegações={evidence['delegations_count']} |"
        )

    lines += [
        "",
        "## Evidência bruta e limitações",
        "",
        "- `records.jsonl` contém a pergunta, resposta integral, fontes/contextos, "
        "delegações, erro, duração, tokens, custo estimado e scores por caso.",
        "- `provenance.json` contém hashes recalculáveis, commit, agregados e totais.",
        "- O custo é uma estimativa equivalente por tokens baseada na tabela versionada "
        "em `config.json`; não é uma fatura emitida pelo provedor.",
        "- Uma lista vazia de fontes demonstra apenas que nenhuma fonte chegou ao estado "
        "final do grafo; não identifica, sozinha, a causa da ausência.",
        "- As decisões de recorte para categorias especiais continuam fora desta "
        "microtarefa e não são inferidas a partir do score heurístico.",
        "",
    ]
    return "\n".join(lines)


def _diagnose_zero_scores(
    records: list[dict[str, Any]],
    *,
    run_id: str,
) -> dict[str, Any]:
    cases = []
    for record in records:
        zero_metrics = [metric for metric in METRIC_NAMES if record["scores"].get(metric) == 0]
        if not zero_metrics:
            continue
        answer = (record["answer"] or "").lower()
        if (
            record["category"] == "fora_de_escopo"
            and "fora do meu escopo" in answer
            and not record["sources"]
            and record["delegations"] == ["fora_de_escopo"]
        ):
            cause = "inadequacao_de_metrica"
            evidence = {
                "answer_contains": "fora do meu escopo",
                "sources_count": 0,
                "delegations_count": 1,
                "heuristic_missing_phrase": "fora do meu escopo",
            }
        else:
            cause = "indeterminada"
            evidence = {
                "answer_contains": "",
                "sources_count": len(record["sources"]),
                "delegations_count": len(record["delegations"]),
                "heuristic_missing_phrase": "",
            }
        cases.append(
            {
                "case_id": record["case_id"],
                "zero_metrics": zero_metrics,
                "cause": cause,
                "evidence": evidence,
            }
        )
    return {"schema_version": "1.0.0", "run_id": run_id, "cases": cases}


async def execute_auditable_baseline(config_path: Path) -> Path:
    """Executa os casos, persistindo resposta, fontes, erro, uso e custo por linha."""
    config = _load_json(config_path)
    if not config["observability"]["external_tracing"]:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
    root = Path.cwd()
    dataset_path = root / config["inputs"]["dataset_path"]
    manifest_path = root / config["inputs"]["manifest_path"]
    output_dir = root / config["output"]["directory"]
    records_path = output_dir / config["output"]["records_file"]
    output_dir.mkdir(parents=True, exist_ok=True)

    cases = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    case_ids = [case["id"] for case in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("dataset contem IDs duplicados")

    existing = load_run_records(records_path) if records_path.exists() else []
    completed = {record["case_id"] for record in existing}
    records = list(existing)
    spent = sum(record["estimated_cost_usd"] for record in records)
    budget = config["budget"]["total_usd"]
    reserve = config["budget"]["per_case_reserve_usd"]

    graph = _carregar_grafo(
        router_model=config["models"]["router"]["name"],
        agent_model=config["models"]["agent"]["name"],
        temperature=config["models"]["agent"]["temperature"],
        max_tokens=config["models"]["agent"]["max_output_tokens"],
        qdrant_url=config["retrieval"]["qdrant_url"],
    )

    for case in cases:
        if case["id"] in completed:
            continue
        if spent + reserve > budget:
            raise BudgetExceededError(
                f"reserva do proximo caso excederia teto; gasto={spent:.6f}, "
                f"reserva={reserve:.6f}, teto={budget:.2f}"
            )

        started_at = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()
        callback = UsageMetadataCallbackHandler()
        invocation_config = {
            "configurable": {"thread_id": f"{config['run_id']}-{case['id']}"},
            "callbacks": [callback],
        }
        try:
            result = await graph.ainvoke(_initial_state(case), invocation_config)
            answer = _extrair_resposta(result)
            scores = _avaliar_resposta(case, answer)
            status = "success"
            error = None
            sources = _serialize_sources(result)
            delegations = [delegation["agent"] for delegation in result.get("delegations", [])]
        except Exception as exc:
            answer = None
            scores = {metric: None for metric in METRIC_NAMES}
            status = "error"
            error = {"type": type(exc).__name__, "message": str(exc) or repr(exc)}
            sources = []
            delegations = []

        usage = _normalize_usage(callback.usage_metadata)
        remaining_budget = budget - spent
        case_cost = estimate_cost_usd(
            usage,
            config["pricing"]["models"],
            budget_usd=remaining_budget,
        )
        record = {
            "schema_version": "1.0.0",
            "run_id": config["run_id"],
            "case_id": case["id"],
            "profile": case["profile"],
            "category": case["category"],
            "question": case["question"],
            "reference_answer": case["reference_answer"],
            "started_at": started_at,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "status": status,
            "answer": answer,
            "sources": sources,
            "delegations": delegations,
            "error": error,
            "usage": usage,
            "estimated_cost_usd": case_cost,
            "scores": scores,
            "score_mechanism": config["scoring"]["mechanism"],
        }
        validate_run_record(record)
        with records_path.open("a", encoding="utf-8", newline="\n") as output:
            output.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        records.append(record)
        spent += case_cost

    source_commit = _git_head()
    dataset_blob = canonical_git_blob_sha1(dataset_path)
    manifest_blob = canonical_git_blob_sha1(manifest_path)
    diagnostics = _diagnose_zero_scores(records, run_id=config["run_id"])
    diagnostics_path = output_dir / "zero_diagnostics.json"
    diagnostics_path.write_text(
        json.dumps(diagnostics, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report_path = output_dir / config["output"]["report_file"]
    report_path.write_text(
        _generate_report(
            records,
            config=config,
            diagnostics=diagnostics,
            source_commit=source_commit,
            dataset_blob=dataset_blob,
            manifest_blob=manifest_blob,
            total_cost=spent,
        ),
        encoding="utf-8",
        newline="\n",
    )

    provenance = {
        "schema_version": "1.0.0",
        "run_id": config["run_id"],
        "source_commit": source_commit,
        "config_path": config_path.resolve().relative_to(root.resolve()).as_posix(),
        "config_git_blob_sha1": canonical_git_blob_sha1(config_path),
        "dataset_path": config["inputs"]["dataset_path"],
        "dataset_git_blob_sha1": dataset_blob,
        "dataset_sha256": canonical_sha256(dataset_path),
        "manifest_path": config["inputs"]["manifest_path"],
        "manifest_git_blob_sha1": manifest_blob,
        "manifest_sha256": canonical_sha256(manifest_path),
        "record_count": len(records),
        "success_count": sum(record["status"] == "success" for record in records),
        "error_count": sum(record["status"] == "error" for record in records),
        "aggregate_scores": compute_aggregate_scores(records),
        "usage": {
            "input_tokens": sum(record["usage"]["input_tokens"] for record in records),
            "output_tokens": sum(record["usage"]["output_tokens"] for record in records),
            "total_tokens": sum(record["usage"]["total_tokens"] for record in records),
        },
        "estimated_cost_usd": spent,
        "budget_usd": budget,
        "records_file": config["output"]["records_file"],
        "records_sha256": canonical_sha256(records_path),
        "report_file": config["output"]["report_file"],
        "report_sha256": canonical_sha256(report_path),
        "zero_diagnostics_file": diagnostics_path.name,
        "zero_diagnostics_sha256": canonical_sha256(diagnostics_path),
    }
    provenance_path = output_dir / config["output"]["provenance_file"]
    provenance_path.write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return provenance_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Executa baseline RAG auditável")
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(execute_auditable_baseline(args.config))
    print(f"Proveniencia gerada em: {result}")


if __name__ == "__main__":
    main()
