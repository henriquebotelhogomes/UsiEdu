"""Contracts for the approved T04.5 technical alerting surfaces."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent
ALERTS_PATH = ROOT / "infra" / "azure" / "monitoring-alerts.bicep"
ACCESS_PATH = ROOT / "infra" / "azure" / "monitoring-access.bicep"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "report-azure-operational-alerts.yml"
DEPLOY_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "configure-azure-operational-alerts.yml"


def _workflow() -> tuple[str, dict]:
    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    return text, yaml.safe_load(text)


def test_alert_rules_use_only_observed_log_schema_and_postgresql_metric() -> None:
    template = ALERTS_PATH.read_text(encoding="utf-8")

    assert "Microsoft.Insights/scheduledQueryRules@2023-12-01" in template
    assert "ContainerAppConsoleLogs_CL" in template
    assert "ContainerAppSystemLogs_CL" in template
    assert "TimeGenerated > ago(5m)" in template
    assert "Stream_s == 'stderr'" in template
    assert "Log_s has 'Traceback'" in template
    assert "timeAggregation: 'Count'" in template
    assert "operator: 'GreaterThan'" in template
    assert "threshold: 0" in template
    assert "param ingestJobName string" in template
    assert "JobName_s == '{ingestJobName}'" in template
    assert "replace(ingestJobFailureQuery, '{ingestJobName}', ingestJobName)" in template
    assert "Reason_s == 'BackoffLimitExceeded'" in template
    assert "Microsoft.Insights/metricAlerts@2018-03-01" in template
    assert "metricName: 'is_db_alive'" in template
    assert "timeAggregation: 'Average'" in template
    assert "operator: 'LessThan'" in template
    assert "threshold: 1" in template
    assert "evaluationFrequency: 'PT5M'" in template
    assert "windowSize: 'PT15M'" in template
    assert "actionGroups" not in template
    assert "budget" not in template.lower()


def test_alert_access_is_scoped_to_resource_group_and_log_workspace() -> None:
    template = ACCESS_PATH.read_text(encoding="utf-8")

    assert "targetScope = 'resourceGroup'" in template
    assert "749f88d5-cbae-40b8-bcfc-e573ddc772fa" in template  # Monitoring Contributor
    assert "73c42c96-874c-492b-b04d-ab87d138a893" in template  # Log Analytics Reader
    assert "scope: logAnalyticsWorkspace" in template
    assert "scope: resourceGroup()" in template
    assert "b24988ac-6180-42a0-ab88-20f7382dd24c" not in template


def test_alert_report_is_manual_protected_and_deduplicates_github_issues() -> None:
    text, workflow = _workflow()
    job = workflow["jobs"]["report"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {
        "contents": "read",
        "id-token": "write",
        "issues": "write",
    }
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "production"
    assert "azure/login@v2" in text
    assert "Microsoft.AlertsManagement/alerts" in text
    assert "usiedu-ingest-failed" in text
    assert "alertState" in text
    assert "gh issue list" in text
    assert "gh issue create" in text
    assert "gh issue comment" in text
    assert "azure-operational-alert" in text
    assert "${{ secrets." not in text.lower()
    assert "webhook" not in text.lower()
    assert "teams" not in text.lower()
    assert "budget" not in text.lower()


def test_alert_deployment_is_manual_protected_and_uses_compiled_templates() -> None:
    text = DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    job = workflow["jobs"]["configure"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "production"
    assert "azure/login@v2" in text
    assert "infra/azure/monitoring-alerts.bicep" in text
    assert "az deployment group create" in text
    assert "az resource show" in text
    assert '"${alert##*/}"' in text
    assert "az monitor scheduled-query" not in text
    assert "${{ secrets." not in text.lower()
