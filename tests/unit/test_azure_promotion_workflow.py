"""Contrato estático do pipeline OIDC de promoção Azure (T03.4)."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "promote-azure.yml"
DOC_PATH = ROOT / "docs" / "profissionalizacao" / "03-integracao-entrega-rollback.md"


def _workflow() -> tuple[str, dict]:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def test_promotion_is_manual_main_only_and_requires_production_approval() -> None:
    text, workflow = _workflow()

    assert set(workflow["on"]) == {"workflow_dispatch"}
    job = workflow["jobs"]["promote"]
    assert job["environment"] == "production"
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert "environment: production" in text


def test_oidc_uses_variables_without_persistent_azure_secret() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["promote"]["steps"]
    login_step = next(step for step in steps if step.get("uses") == "azure/login@v2")
    step_names = [step.get("name") for step in steps]

    assert login_step["with"] == {
        "client-id": "${{ vars.AZURE_CLIENT_ID }}",
        "tenant-id": "${{ vars.AZURE_TENANT_ID }}",
        "subscription-id": "${{ vars.AZURE_SUBSCRIPTION_ID }}",
    }
    lowered = text.lower()
    assert "${{ secrets." not in lowered
    assert "client-secret" not in lowered
    assert "password" not in lowered
    assert step_names.index("Prepare evidence directory") < step_names.index(
        "Login to Azure with OIDC"
    )


def test_candidate_is_sha_tagged_scanned_and_policy_gated_before_push() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["promote"]["steps"]
    step_names = [step.get("name") for step in steps]
    scan_actions = {
        step["uses"]
        for step in steps
        if step.get("name") in {"Scan API candidate", "Scan frontend candidate"}
    }

    assert "${{ github.sha }}" in text
    assert ":latest" not in text.lower()
    assert scan_actions == {"aquasecurity/trivy-action@ed142fd0673e97e23eac54620cfb913e5ce36c25"}
    scan_steps = [
        step
        for step in steps
        if step.get("name") in {"Scan API candidate", "Scan frontend candidate"}
    ]
    assert len(scan_steps) == 2
    assert all(
        step["with"].get("cache") == "true"
        and step["with"].get("version") == "v0.73.0"
        and step["env"]["TRIVY_CACHE_BACKEND"] == "memory"
        for step in scan_steps
    )
    assert "Scan API candidate" in step_names
    assert "Scan frontend candidate" in step_names
    assert "Enforce image policy" in step_names
    assert "Push immutable candidates" in step_names
    assert step_names.index("Enforce image policy") < step_names.index("Push immutable candidates")
    assert "src/delivery/image_policy_v1.json" in text


def test_deploy_records_previous_and_new_digest_references() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["promote"]["steps"]
    deploy = next(step for step in steps if step.get("name") == "Deploy approved digests")
    evidence = next(step for step in steps if step.get("name") == "Write promotion evidence")

    assert "az containerapp show" in deploy["run"]
    assert "previous-api-image" in deploy["run"]
    assert "previous-frontend-image" in deploy["run"]
    assert "az containerapp update" in deploy["run"]
    assert '--image "$API_REF"' in deploy["run"]
    assert '--image "$FRONTEND_REF"' in deploy["run"]
    assert "github_sha" in evidence["run"]
    assert "api_ref" in evidence["run"]
    assert "frontend_ref" in evidence["run"]
    assert "previous_api_ref" in evidence["run"]
    assert "previous_frontend_ref" in evidence["run"]
    assert "Upload promotion evidence" in [step.get("name") for step in steps]
    assert "if: always()" in text


def test_documentation_records_hosted_execution_gate() -> None:
    document = DOC_PATH.read_text(encoding="utf-8")

    assert "- [x] **T03.4 — Criar pipeline de promoção**" in document
    assert "identidade OIDC e Environment `production` configurados" in document
    assert "o scan usa Trivy `v0.73.0` com cache de análise em memória" in document
    assert "31624834815" in document
    assert "repo:henriquebotelhogomes@43866427/UsiEdu@1324468469:environment:production" in document
