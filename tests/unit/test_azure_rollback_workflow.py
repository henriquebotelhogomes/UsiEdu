"""Contrato estático do rollback Azure controlado (T03.5)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "rollback-azure.yml"


def _workflow() -> tuple[str, dict]:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def test_rollback_is_manual_main_only_and_requires_production_approval() -> None:
    text, workflow = _workflow()
    rollback = workflow["jobs"]["rollback"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert rollback["if"] == "github.ref == 'refs/heads/main'"
    assert rollback["environment"] == "production"
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert "${{ secrets." not in text.lower()
    assert "client-secret" not in text.lower()


def test_rollback_uses_only_preserved_digest_inputs_and_never_rebuilds_images() -> None:
    text, workflow = _workflow()
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    steps = workflow["jobs"]["rollback"]["steps"]
    step_names = [step.get("name") for step in steps]

    assert set(inputs) == {"api_digest", "frontend_digest"}
    assert all(value["required"] is True for value in inputs.values())
    assert "^sha256:[0-9a-f]{64}$" in text
    assert "${{ inputs.api_digest }}" in text
    assert "${{ inputs.frontend_digest }}" in text
    assert "docker build" not in text
    assert "docker push" not in text
    assert step_names.index("Capture rollback baseline") < step_names.index(
        "Deploy preserved rollback digests"
    )


def test_rollback_records_revisions_and_runs_public_smokes_after_deploy() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["rollback"]["steps"]
    deploy = next(step for step in steps if step.get("name") == "Deploy preserved rollback digests")
    evidence = next(step for step in steps if step.get("name") == "Write rollback evidence")
    step_names = [step.get("name") for step in steps]

    assert "az containerapp update" in deploy["run"]
    assert "API_ROLLBACK_REF" in deploy["run"]
    assert "FRONTEND_ROLLBACK_REF" in deploy["run"]
    assert step_names.index("Deploy preserved rollback digests") < step_names.index(
        "Smoke test public health"
    )
    assert step_names.index("Smoke test public health") < step_names.index(
        "Run authenticated public smoke"
    )
    assert "python -m src.delivery.rollback_smoke" in text
    assert "previous_api_ref" in evidence["run"]
    assert "previous_frontend_ref" in evidence["run"]
    assert "rollback_api_ref" in evidence["run"]
    assert "rollback_frontend_ref" in evidence["run"]
    assert "if: always()" in text
