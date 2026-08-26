"""Testes determinísticos do inventário operacional T04.1."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from src.observability.logging import JSONFormatter
from src.security.operational_hygiene import (
    contains_simulated_secret,
    redact_sensitive_fields,
)


def test_simulated_secret_detection_distinguishes_values_from_variable_names() -> None:
    assert contains_simulated_secret("OPENCODE_GO_API_KEY=simulated-secret-value")
    assert contains_simulated_secret('{"password": "simulated-password"}')
    assert not contains_simulated_secret("OPENCODE_GO_API_KEY=")
    assert not contains_simulated_secret("secretRef: opencode-api-key")


def test_log_redaction_masks_sensitive_fields_recursively() -> None:
    event = {
        "status": "ok",
        "authorization": "Bearer simulated-token",
        "metadata": {"password": "simulated-password", "trace_id": "safe-trace"},
    }

    redacted = redact_sensitive_fields(event)

    assert redacted == {
        "status": "ok",
        "authorization": "[REDACTED]",
        "metadata": {"password": "[REDACTED]", "trace_id": "safe-trace"},
    }
    assert event["authorization"] == "Bearer simulated-token"


def test_json_logging_never_serializes_sensitive_extra_values() -> None:
    record = logging.LogRecord(
        name="usiedu.security",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="operational event",
        args=(),
        exc_info=None,
    )
    record.authorization = "Bearer simulated-token"
    record.payload = {"jwt": "simulated-jwt", "status": "ok"}

    rendered = json.loads(JSONFormatter().format(record))

    assert rendered["authorization"] == "[REDACTED]"
    assert rendered["payload"] == {"jwt": "[REDACTED]", "status": "ok"}


def test_operational_inventory_is_versioned_and_contains_only_references() -> None:
    inventory_path = Path("src/security/operational_inventory_v1.json")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))

    assert inventory["schema_version"] == "1.0.0"
    assert inventory["scope"] == "T04.1"
    assert set(inventory) == {
        "schema_version",
        "scope",
        "classification_rules",
        "assets",
        "gates",
    }
    assert {asset["id"] for asset in inventory["assets"]} >= {
        "runtime-secrets",
        "telemetry",
        "persistent-state",
        "deployment-permissions",
    }
    assert all(not contains_simulated_secret(json.dumps(asset)) for asset in inventory["assets"])
    assert all(
        Path(path).is_file() for asset in inventory["assets"] for path in asset["evidence_paths"]
    )
