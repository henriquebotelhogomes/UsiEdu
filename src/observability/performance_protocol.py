"""Validação sanitizada do protocolo de medição de performance da T05.1."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
LOAD_PROFILE = {"concurrent_users": 5, "burst_requests": 10}
TEMPERATURES = {"cold", "warm"}
SCENARIOS = {"health", "login", "chat"}
MODEL_KEYS = {"router", "agent", "embedder", "reranker"}
DEPENDENCY_KEYS = {"llm", "qdrant", "postgresql"}
DEPENDENCY_OUTCOMES = {"not_measured", "healthy", "unavailable", "timeout", "error"}
SENSITIVE_FIELDS = {
    "answer",
    "authorization",
    "content",
    "email",
    "jwt",
    "message",
    "password",
    "question",
    "secret",
    "session_id",
    "token",
}


def _require_mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _require_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _require_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be a number")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return float(value)


def _parse_timestamp(value: object, field: str) -> datetime:
    timestamp = _require_string(value, field)
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def _reject_sensitive_fields(value: object) -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key.lower() in SENSITIVE_FIELDS:
                raise ValueError(f"sensitive field is prohibited: {key}")
            _reject_sensitive_fields(nested_value)
    elif isinstance(value, list):
        for nested_value in value:
            _reject_sensitive_fields(nested_value)


def _validate_sample(value: object) -> dict[str, Any]:
    sample = _require_mapping(value, "sample")
    _require_string(sample.get("sample_id"), "sample.sample_id")

    temperature = _require_string(sample.get("temperature"), "sample.temperature")
    if temperature not in TEMPERATURES:
        raise ValueError("sample.temperature must be cold or warm")

    scenario = _require_string(sample.get("scenario"), "sample.scenario")
    if scenario not in SCENARIOS:
        raise ValueError("sample.scenario must be health, login, or chat")

    started_at = _parse_timestamp(sample.get("started_at"), "sample.started_at")
    completed_at = _parse_timestamp(sample.get("completed_at"), "sample.completed_at")
    if completed_at < started_at:
        raise ValueError("sample.completed_at must not precede sample.started_at")

    _require_string(sample.get("revision"), "sample.revision")

    replica_count = sample.get("replica_count")
    if isinstance(replica_count, bool) or not isinstance(replica_count, int) or replica_count < 0:
        raise ValueError("sample.replica_count must be a non-negative integer")

    models = _require_mapping(sample.get("models"), "sample.models")
    if set(models) != MODEL_KEYS:
        raise ValueError("sample.models must declare router, agent, embedder, and reranker")
    for name, model in models.items():
        _require_string(model, f"sample.models.{name}")

    status_code = sample.get("status_code")
    if (
        isinstance(status_code, bool)
        or not isinstance(status_code, int)
        or not 100 <= status_code <= 599
    ):
        raise ValueError("sample.status_code must be an HTTP status code")

    latency_ms = _require_mapping(sample.get("latency_ms"), "sample.latency_ms")
    _require_number(latency_ms.get("total"), "sample.latency_ms.total")
    if scenario == "chat":
        _require_number(latency_ms.get("first_token"), "sample.latency_ms.first_token")
    elif "first_token" in latency_ms:
        raise ValueError("sample.latency_ms.first_token is only valid for chat")

    dependency_outcomes = _require_mapping(
        sample.get("dependency_outcomes"), "sample.dependency_outcomes"
    )
    if set(dependency_outcomes) != DEPENDENCY_KEYS:
        raise ValueError("sample.dependency_outcomes must declare llm, qdrant, and postgresql")
    if not set(dependency_outcomes.values()) <= DEPENDENCY_OUTCOMES:
        raise ValueError("sample.dependency_outcomes contains an invalid value")

    if not isinstance(sample.get("exit_137_observed"), bool):
        raise ValueError("sample.exit_137_observed must be boolean")

    return sample


def validate_and_split_samples(report: object) -> dict[str, list[dict[str, Any]]]:
    """Valida o relatório sanitizado e o separa por amostras cold e warm."""
    _reject_sensitive_fields(report)
    validated = _require_mapping(report, "report")

    if validated.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"report.schema_version must be {SCHEMA_VERSION}")
    if validated.get("evidence_kind") not in {
        "performance_measurement",
        "performance_protocol_self_test",
    }:
        raise ValueError("report.evidence_kind is invalid")
    if validated.get("environment") not in {"local", "azure"}:
        raise ValueError("report.environment must be local or azure")
    if validated.get("load_profile") != LOAD_PROFILE:
        raise ValueError("report.load_profile must use the approved load profile")

    samples = validated.get("samples")
    if not isinstance(samples, list) or not samples:
        raise ValueError("report.samples must be a non-empty array")

    separated: dict[str, list[dict[str, Any]]] = {"cold": [], "warm": []}
    for sample in samples:
        validated_sample = _validate_sample(sample)
        separated[validated_sample["temperature"]].append(validated_sample)

    if not separated["cold"] or not separated["warm"]:
        raise ValueError("report.samples must include cold and warm samples")
    return separated


def main() -> None:
    """Valida um arquivo JSON e imprime suas amostras separadas por temperatura."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Caminho para o relatório JSON sanitizado.")
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    print(json.dumps(validate_and_split_samples(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
