"""Contrato estático do exercício isolado de recuperação T04.4."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "exercise-azure-recovery.yml"


def _workflow() -> tuple[str, dict]:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def test_recovery_is_manual_main_only_and_production_protected() -> None:
    text, workflow = _workflow()
    job = workflow["jobs"]["recover"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "production"
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert "${{ secrets." not in text.lower()


def test_recovery_requires_an_isolated_postgresql_target_and_share_clone() -> None:
    _, workflow = _workflow()
    job = workflow["jobs"]["recover"]
    steps = job["steps"]
    restore = next(step for step in steps if step["name"] == "Restore isolated PostgreSQL")
    qdrant = next(step for step in steps if step["name"] == "Snapshot and clone Qdrant share")

    assert job["env"]["RECOVERY_RESOURCE_GROUP"] == ("${{ vars.AZURE_RECOVERY_RESOURCE_GROUP }}")
    assert job["env"]["RECOVERY_POSTGRES_SERVER"] == ("${{ vars.AZURE_RECOVERY_POSTGRES_SERVER }}")
    assert "az postgres flexible-server restore" in restore["run"]
    assert '--resource-group "$RECOVERY_RESOURCE_GROUP"' in restore["run"]
    assert '--name "$RECOVERY_POSTGRES_SERVER"' in restore["run"]
    assert '"$RECOVERY_POSTGRES_SERVER" != "$SOURCE_POSTGRES_SERVER"' in restore["run"]
    assert "az storage share-rm snapshot" in qdrant["run"]
    assert "--query snapshotTime -o tsv" in qdrant["run"]
    assert "properties.shareSnapshot" not in qdrant["run"]
    assert "azure-storage-file-share==12.23.0" in qdrant["run"]
    assert "generate_account_sas" in qdrant["run"]
    assert "Services(fileshare=True)" in qdrant["run"]
    assert "ResourceTypes(container=True, object=True)" in qdrant["run"]
    assert "AccountSasPermissions(read=True, list=True)" in qdrant["run"]
    assert "AccountSasPermissions(write=True, create=True, list=True)" in qdrant["run"]
    assert (
        '"https://${STORAGE_ACCOUNT}.file.core.windows.net/${SOURCE_SHARE}?sharesnapshot=${QDRANT_SNAPSHOT}&${SOURCE_SAS}"'
        in qdrant["run"]
    )
    assert (
        '"https://${STORAGE_ACCOUNT}.file.core.windows.net/${RECOVERY_SHARE}?${DESTINATION_SAS}"'
        in (qdrant["run"])
    )
    assert "az storage share create" in qdrant["run"]
    assert "command -v azcopy" in qdrant["run"]
    assert "azcopy copy" in qdrant["run"]
    assert "--recursive=true" in qdrant["run"]
    assert "az storage file copy start-batch" not in qdrant["run"]
    assert 'RECOVERY_SHARE="qdrant-recovery-${GITHUB_RUN_ID}"' in qdrant["run"]
    assert qdrant["run"].index('echo "RECOVERY_SHARE=$RECOVERY_SHARE"') < qdrant["run"].index(
        "azcopy copy"
    )
    assert qdrant["run"].index('echo "QDRANT_SNAPSHOT=$QDRANT_SNAPSHOT"') < qdrant["run"].index(
        "azcopy copy"
    )


def test_recovery_validates_without_printing_credentials_or_persisted_content() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["recover"]["steps"]
    validation = next(step for step in steps if step["name"] == "Validate recovered resources")
    postgresql = next(
        step for step in steps if step["name"] == "Validate recovered PostgreSQL query"
    )
    evidence = next(step for step in steps if step["name"] == "Write recovery evidence")

    assert "az postgres flexible-server show" in validation["run"]
    assert "az storage share show" in validation["run"]
    job_env = workflow["jobs"]["recover"]["env"]
    assert job_env["KEY_VAULT_NAME"] == "${{ vars.AZURE_KEY_VAULT_NAME }}"
    assert "az postgres flexible-server firewall-rule create" in postgresql["run"]
    assert '--resource-group "$RECOVERY_RESOURCE_GROUP"' in postgresql["run"]
    assert "--name allow-azure-services" in postgresql["run"]
    assert "az keyvault secret show" in postgresql["run"]
    assert "--name database-url" in postgresql["run"]
    assert "psycopg[binary]" in postgresql["run"]
    assert "SELECT 1" in postgresql["run"]
    assert "az storage file list" not in text
    assert "az postgres flexible-server db" not in text
    assert "az storage account keys list" in text
    assert "--output none" in text
    assert "STORAGE_KEY" not in evidence["run"]
    assert "DATABASE_URL" not in evidence["run"]
    assert "postgresql_connectivity_validated" in evidence["run"]
    assert "RECOVERY_POSTGRES_SERVER" in evidence["run"]
    assert "RECOVERY_SHARE" in evidence["run"]
    assert "Upload recovery evidence" in [step["name"] for step in steps]


def test_recovery_records_rpo_rto_measurement_and_never_deletes_production() -> None:
    text, workflow = _workflow()
    steps = workflow["jobs"]["recover"]["steps"]
    evidence = next(step for step in steps if step["name"] == "Write recovery evidence")
    cleanup = next(step for step in steps if step["name"] == "Clean up isolated recovery resources")

    assert "rpo_target_hours" in evidence["run"]
    assert "rto_target_hours" in evidence["run"]
    assert "restore_started_at" in evidence["run"]
    assert "restore_completed_at" in evidence["run"]
    assert '--resource-group "$RECOVERY_RESOURCE_GROUP"' in cleanup["run"]
    assert '"$RECOVERY_POSTGRES_SERVER" != "$SOURCE_POSTGRES_SERVER"' in cleanup["run"]
    assert "az postgres flexible-server list" in cleanup["run"]
    assert "az postgres flexible-server show" not in cleanup["run"]
    assert "SOURCE_POSTGRES_SERVER" not in cleanup["run"].replace(
        '"$RECOVERY_POSTGRES_SERVER" != "$SOURCE_POSTGRES_SERVER"', ""
    )


def test_recovery_retries_only_one_transient_postgresql_restore_failure() -> None:
    _, workflow = _workflow()
    steps = workflow["jobs"]["recover"]["steps"]
    restore = next(step for step in steps if step["name"] == "Restore isolated PostgreSQL")

    assert "for attempt in 1 2" in restore["run"]
    assert 'test "$attempt" -eq 2' in restore["run"]
    assert "sleep 30" in restore["run"]
    assert restore["run"].count("az postgres flexible-server restore") == 1
