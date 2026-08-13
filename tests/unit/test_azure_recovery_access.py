"""Contrato de menor privilégio para o exercício de recuperação T04.4."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
SOURCE_ACCESS_PATH = ROOT / "infra" / "azure" / "recovery-source-access.bicep"
TARGET_ACCESS_PATH = ROOT / "infra" / "azure" / "recovery-target-access.bicep"


def test_source_access_is_limited_to_restore_read_and_qdrant_clone_actions() -> None:
    template = SOURCE_ACCESS_PATH.read_text(encoding="utf-8")

    assert "param deploymentPrincipalId string" in template
    assert "Microsoft.DBforPostgreSQL/flexibleServers" in template
    assert "Microsoft.Storage/storageAccounts" in template
    assert "acdd72a7-3385-48ef-bd42-f606fba81ae7" in template  # Reader
    assert "17d1049b-9a84-46fb-8f53-869881c3d3ab" in template  # Storage Account Contributor
    assert "81a9662b-bebf-436f-a333-f67b29880f12" in template  # Storage Account Key Operator
    assert "scope: postgresServer" in template
    assert template.count("scope: storageAccount") == 2
    assert "b24988ac-6180-42a0-ab88-20f7382dd24c" not in template


def test_target_access_is_contributor_only_in_the_isolated_resource_group() -> None:
    template = TARGET_ACCESS_PATH.read_text(encoding="utf-8")

    assert "targetScope = 'resourceGroup'" in template
    assert "param deploymentPrincipalId string" in template
    assert "b24988ac-6180-42a0-ab88-20f7382dd24c" in template  # Contributor
    assert "Microsoft.DBforPostgreSQL/flexibleServers" not in template
    assert "Microsoft.Storage/storageAccounts" not in template
