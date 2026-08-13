"""Contrato estático da migração T04.2 para Key Vault e Managed Identity."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "migrate-azure-secrets.yml"
FOUNDATION_PATH = ROOT / "infra" / "azure" / "security-foundation.bicep"


def _workflow() -> tuple[str, dict]:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def test_secret_migration_is_manual_main_only_and_production_protected() -> None:
    text, workflow = _workflow()
    job = workflow["jobs"]["migrate"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "production"
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert "${{ secrets." not in text.lower()


def test_migration_copies_active_values_without_printing_them() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["migrate"]["steps"]
    names = [step["name"] for step in steps]
    migration = next(step for step in steps if step["name"] == "Migrate active secrets")

    assert "az containerapp secret show" in migration["run"]
    assert "az keyvault secret set" in migration["run"]
    assert "--output none" in migration["run"]
    assert "set -euo pipefail" in migration["run"]
    assert names.index("Validate secret migration prerequisites") < names.index(
        "Migrate active secrets"
    )
    prerequisites = next(
        step for step in steps if step["name"] == "Validate secret migration prerequisites"
    )
    assert "az identity show" in prerequisites["run"]
    assert "az role assignment list" not in prerequisites["run"]


def test_migration_uses_user_assigned_identity_and_preserves_jwt() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["migrate"]["steps"]
    migration = next(step for step in steps if step["name"] == "Migrate active secrets")

    assert "az containerapp identity assign" in migration["run"]
    assert '--user-assigned "$RUNTIME_IDENTITY_ID"' in migration["run"]
    assert "az containerapp registry set" in migration["run"]
    assert "az containerapp job identity assign" in migration["run"]
    assert "validate_ingest_job_identity" in migration["run"]
    assert "az containerapp job show" in migration["run"]
    assert "jq -e" in migration["run"]
    assert "az containerapp job registry set" in migration["run"]
    assert "az containerapp secret remove" in migration["run"]
    assert "az containerapp job secret remove" in migration["run"]
    assert "identityref:${RUNTIME_IDENTITY_ID}" in migration["run"]
    assert "keyvaultref:" in migration["run"]
    assert "jwt-secret" in migration["run"]
    assert migration["run"].count("registry-password") == 3
    disable_admin = next(step for step in steps if step["name"] == "Disable legacy ACR admin")
    assert "az acr update" in disable_admin["run"]
    assert "--admin-enabled false" in disable_admin["run"]


def test_migration_writes_sanitized_evidence_and_smoke_tests_result() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["migrate"]["steps"]
    names = [step["name"] for step in steps]

    assert "Smoke test migrated deployment" in names
    assert "Restart migrated API revision" in names
    assert "Disable legacy ACR admin" in names
    assert "Write migration evidence" in names
    assert "Upload migration evidence" in names
    assert names.index("Migrate active secrets") < names.index("Restart migrated API revision")
    assert names.index("Restart migrated API revision") < names.index(
        "Smoke test migrated deployment"
    )
    assert names.index("Smoke test migrated deployment") < names.index("Disable legacy ACR admin")
    assert (
        "jwt"
        not in next(
            step["run"] for step in steps if step["name"] == "Write migration evidence"
        ).lower()
    )


def test_security_foundation_uses_rbac_key_vault_and_least_privilege_identity() -> None:
    template = FOUNDATION_PATH.read_text(encoding="utf-8")

    assert "Microsoft.KeyVault/vaults" in template
    assert "enableRbacAuthorization: true" in template
    assert "Microsoft.ManagedIdentity/userAssignedIdentities" in template
    assert "7f951dda-4ed3-4680-a7ca-43fe172d538d" in template  # AcrPull
    assert "4633458b-17de-408a-b874-0445c86b69e6" in template  # Key Vault Secrets User
    assert "b86a8fe4-44ce-4948-aee5-eccb2c155cd7" in template  # Key Vault Secrets Officer
    assert "358470bc-b998-42bd-ab17-a7e34c199c0f" in template  # Container Apps Contributor
    assert "b24988ac-6180-42a0-ab88-20f7382dd24c" in template  # Contributor on ACR
    assert "4e3d2b60-56ae-4dc6-a233-09c8e5a82e68" in template  # Container Apps Jobs Contributor
    assert "@secure()" not in template
    assert "param jwtSecret" not in template
