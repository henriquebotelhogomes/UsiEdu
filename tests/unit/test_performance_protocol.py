"""Contratos determinísticos do protocolo de medição da T05.1."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.observability.performance_protocol import validate_and_split_samples

ROOT = Path(__file__).parent.parent.parent
PROTOCOL_PATH = ROOT / "src" / "observability" / "performance_protocol_v1.json"
SELF_TEST_PATH = ROOT / "src" / "observability" / "performance_protocol_self_test_v1.json"


def _sample(*, temperature: str, scenario: str) -> dict[str, object]:
    latency_ms: dict[str, float] = {"total": 45.0}
    if scenario == "chat":
        latency_ms["first_token"] = 18.0

    return {
        "sample_id": f"{temperature}-{scenario}-001",
        "temperature": temperature,
        "scenario": scenario,
        "started_at": "2026-08-17T19:40:00Z",
        "completed_at": "2026-08-17T19:40:01Z",
        "revision": "local-test",
        "replica_count": 1,
        "models": {
            "router": "fake-router",
            "agent": "fake-agent",
            "embedder": "fake-embedder",
            "reranker": "fake-reranker",
        },
        "status_code": 200,
        "latency_ms": latency_ms,
        "dependency_outcomes": {
            "llm": "not_measured",
            "qdrant": "not_measured",
            "postgresql": "not_measured",
        },
        "exit_137_observed": False,
    }


def _report() -> dict[str, object]:
    return {
        "schema_version": "1.0.0",
        "evidence_kind": "performance_protocol_self_test",
        "environment": "local",
        "load_profile": {"concurrent_users": 5, "burst_requests": 10},
        "samples": [
            _sample(temperature="cold", scenario="health"),
            _sample(temperature="warm", scenario="login"),
            _sample(temperature="warm", scenario="chat"),
        ],
    }


def test_protocol_declares_approved_load_and_sensitive_data_exclusions() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))

    assert protocol["schema_version"] == "1.0.0"
    assert protocol["load_profile"] == {"concurrent_users": 5, "burst_requests": 10}
    assert protocol["temperatures"] == ["cold", "warm"]
    assert protocol["scenarios"] == ["health", "login", "chat"]
    assert "ttft" in protocol["metrics"]
    assert "question" in protocol["prohibited_fields"]
    assert "answer" in protocol["prohibited_fields"]
    assert "jwt" in protocol["prohibited_fields"]


def test_validated_report_separates_cold_and_warm_samples() -> None:
    separated = validate_and_split_samples(_report())

    assert [sample["scenario"] for sample in separated["cold"]] == ["health"]
    assert [sample["scenario"] for sample in separated["warm"]] == ["login", "chat"]
    assert separated["cold"][0]["revision"] == "local-test"
    assert separated["warm"][1]["latency_ms"]["first_token"] == 18.0


def test_protocol_rejects_sensitive_content_and_invalid_chat_ttft() -> None:
    sensitive_report = copy.deepcopy(_report())
    sensitive_report["samples"][0]["question"] = "conteudo que nao pode ser medido"

    with pytest.raises(ValueError, match="sensitive field"):
        validate_and_split_samples(sensitive_report)

    missing_ttft_report = copy.deepcopy(_report())
    del missing_ttft_report["samples"][2]["latency_ms"]["first_token"]

    with pytest.raises(ValueError, match="first_token"):
        validate_and_split_samples(missing_ttft_report)


def test_protocol_self_test_is_sanitized_and_exercises_both_temperatures() -> None:
    self_test = json.loads(SELF_TEST_PATH.read_text(encoding="utf-8"))

    separated = validate_and_split_samples(self_test)

    assert self_test["evidence_kind"] == "performance_protocol_self_test"
    assert len(separated["cold"]) == 1
    assert len(separated["warm"]) == 2
