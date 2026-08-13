"""Contratos determinísticos de minimização de telemetria da T04.3."""

from __future__ import annotations

import json
import logging
import sys
import types
import uuid
from pathlib import Path

from src.api import feedback
from src.api.chat_common import build_run_config
from src.observability import tracing
from src.observability.logging import JSONFormatter

ROOT = Path(__file__).parent.parent.parent
AZURE_TEMPLATE = ROOT / "infra" / "azure" / "main.bicep"
TELEMETRY_WORKFLOW = ROOT / ".github" / "workflows" / "minimize-azure-telemetry.yml"


def test_json_logs_redact_personal_identifiers_and_message_content() -> None:
    record = logging.LogRecord(
        name="usiedu.privacy",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="chat event",
        args=(),
        exc_info=None,
    )
    record.user_email = "demo.user@example.test"
    record.session_id = "synthetic-session-123"
    record.question = "synthetic question content"
    record.answer = "synthetic answer content"

    rendered = json.loads(JSONFormatter().format(record))

    assert rendered["user_email"] == "[REDACTED]"
    assert rendered["session_id"] == "[REDACTED]"
    assert rendered["question"] == "[REDACTED]"
    assert rendered["answer"] == "[REDACTED]"


def test_langsmith_run_metadata_omits_user_and_session_identifiers() -> None:
    user = {"email": "demo.user@example.test", "profile": "student"}
    session_id = "synthetic-session-123"

    config = build_run_config(user, session_id, uuid.uuid4())

    assert config["configurable"]["thread_id"] == session_id
    assert "user_email" not in config["metadata"]
    assert "session_id" not in config["metadata"]
    assert "demo.user@example.test" not in json.dumps(config["metadata"])


def test_production_tracing_hides_inputs_and_outputs_and_has_a_protected_runbook() -> None:
    template = AZURE_TEMPLATE.read_text(encoding="utf-8")
    workflow = TELEMETRY_WORKFLOW.read_text(encoding="utf-8")

    assert "LANGSMITH_HIDE_INPUTS" in template
    assert "LANGSMITH_HIDE_OUTPUTS" in template
    assert "value: 'true'" in template
    assert "environment: production" in workflow
    assert "LANGSMITH_HIDE_INPUTS=true" in workflow
    assert "LANGSMITH_HIDE_OUTPUTS=true" in workflow


def test_langsmith_client_hides_inputs_and_outputs(monkeypatch) -> None:
    created_with: dict[str, object] = {}

    class FakeClient:
        def __init__(self, **kwargs: object) -> None:
            created_with.update(kwargs)

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setattr(tracing, "LangSmithClient", FakeClient)
    monkeypatch.setattr(tracing, "_client", None)

    tracing.get_langsmith_client()

    assert created_with == {"hide_inputs": True, "hide_outputs": True}


def test_langsmith_feedback_omits_freeform_comment(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeClient:
        def create_feedback(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setitem(sys.modules, "langsmith", types.SimpleNamespace(Client=FakeClient))

    feedback._envia_feedback_langsmith(str(uuid.uuid4()), "up", "synthetic freeform comment")

    assert captured["comment"] is None
