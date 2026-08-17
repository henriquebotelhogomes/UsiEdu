"""Contratos do medidor protegido de baseline da T05.1."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.observability.performance_baseline import (
    classify_temperature,
    require_uncached_final_event,
    sanitize_status,
)

ROOT = Path(__file__).parent.parent.parent
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "measure-azure-performance-baseline.yml"
OBSERVABILITY_INIT_PATH = ROOT / "src" / "observability" / "__init__.py"


def test_baseline_classifies_cold_only_when_no_replicas_are_running() -> None:
    assert classify_temperature(0) == "cold"
    assert classify_temperature(1) == "warm"


def test_baseline_sanitizes_failures_without_error_or_response_content() -> None:
    status = sanitize_status(status_code=500, error=RuntimeError("sensitive failure detail"))

    assert status == {"status_code": 500, "outcome": "transport_error"}
    assert "sensitive" not in str(status)


def test_baseline_rejects_chat_samples_served_from_cache() -> None:
    with pytest.raises(ValueError, match="cache"):
        require_uncached_final_event({"event": "final", "from_cache": True})


def test_baseline_workflow_is_protected_sanitized_and_uses_approved_load() -> None:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    job = workflow["jobs"]["measure"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "production"
    assert "PERFORMANCE_DEMO_EMAIL" in text
    assert "PERFORMANCE_DEMO_PASSWORD" in text
    assert "AZURE_FRONTEND_APP" in text
    assert "concurrent-users 5" in text
    assert "burst-requests 10" in text
    assert "virtual sessions share one demo account" in text
    assert "az containerapp replica list" in text
    assert 'python -m pip install --quiet "httpx==0.28.1"' in text
    assert "python -m src.observability.performance_baseline" in text
    assert "PERFORMANCE_DEMO_EMAIL" not in text.split("Upload sanitized baseline evidence")[1]
    assert "PERFORMANCE_DEMO_PASSWORD" not in text.split("Upload sanitized baseline evidence")[1]
    assert "${{ secrets." in text


def test_observability_package_does_not_eagerly_import_langsmith_tracing() -> None:
    package_init = OBSERVABILITY_INIT_PATH.read_text(encoding="utf-8")

    assert "from src.observability.tracing import" not in package_init
    assert "def __getattr__(name: str)" in package_init
