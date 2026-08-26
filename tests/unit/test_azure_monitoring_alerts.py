"""Contracts for the approved T04.5 technical alerting surfaces."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent.parent
ALERTS_PATH = ROOT / "infra" / "azure" / "monitoring-alerts.bicep"
ACCESS_PATH = ROOT / "infra" / "azure" / "monitoring-access.bicep"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "report-azure-operational-alerts.yml"
DEPLOY_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "configure-azure-operational-alerts.yml"
SIMULATION_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "exercise-azure-log-alerts.yml"
POSTGRES_SIMULATION_WORKFLOW_PATH = (
    ROOT / ".github" / "workflows" / "exercise-azure-postgresql-alert.yml"
)
POSTGRES_VALIDATION_TEMPLATE_PATH = ROOT / "infra" / "azure" / "postgresql-alert-validation.bicep"
FINANCIAL_BUDGET_TEMPLATE_PATH = ROOT / "infra" / "azure" / "financial-budget.bicep"
FINANCIAL_BUDGET_ACCESS_PATH = ROOT / "infra" / "azure" / "financial-budget-access.bicep"
FINANCIAL_BUDGET_DEPLOY_WORKFLOW_PATH = (
    ROOT / ".github" / "workflows" / "configure-azure-financial-budget.yml"
)
FINANCIAL_BUDGET_REPORT_WORKFLOW_PATH = (
    ROOT / ".github" / "workflows" / "report-azure-financial-budget.yml"
)


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
    assert "api-version=2019-03-01" in text
    assert "2023-07-12-preview" not in text
    assert "usiedu-ingest-failed" in text
    assert "alertState" in text
    assert "group_by(.rule)" in text
    assert "map(max_by(.fired_at))" in text
    assert "gh issue list" in text
    assert "gh issue create" in text
    assert "gh issue comment" in text
    assert "gh issue close" in text
    assert "--reason duplicate" in text
    assert "--duplicate-of" in text
    assert "Consolidated into" in text
    assert "azure-operational-alert" in text
    assert "${{ secrets." not in text.lower()
    assert "webhook" not in text.lower()
    assert "teams" not in text.lower()
    assert "budget" not in text.lower()
    assert "if-no-files-found: warn" in text


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


def test_log_alert_simulation_is_protected_reversible_and_does_not_touch_data_stores() -> None:
    text = SIMULATION_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    job = workflow["jobs"]["simulate"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "production"
    assert "INGEST_JOB: ${{ vars.AZURE_INGEST_JOB }}" in text
    assert '--name "$INGEST_JOB"' in text
    assert "--name usiedu-ingest" not in text
    assert "az containerapp job update" in text
    assert "--replica-retry-limit 1" in text
    assert "--method patch" in text
    assert "Content-Type=application/json" in text
    assert "replicaRetryLimit" in text
    assert "trap restore_retry_limit EXIT" in text
    assert "az containerapp job start" in text
    assert "--command python" in text
    assert "INGEST_IMAGE" in text
    assert '--image "$INGEST_IMAGE"' in text
    assert "CONTROLLED_FAILURE_ARGUMENT" in text
    assert '--args="$CONTROLLED_FAILURE_ARGUMENT"' in text
    assert "Traceback (controlled alert simulation)" in text
    assert "BackoffLimitExceeded" in text
    assert text.count("--query '[0].Count' -o tsv") == 2
    assert "traceback_signal_observed: (($traceback_count | tonumber) > 0)" in text
    assert "ingest_failure_signal_observed: (($ingest_failure_count | tonumber) > 0)" in text
    assert "Microsoft.AlertsManagement/alerts" in text
    assert "api-version=2019-03-01" in text
    assert "usiedu-containerapp-tracebacks" in text
    assert "usiedu-ingest-failed" in text
    assert "az postgres flexible-server" not in text
    assert "QDRANT_URL" not in text
    assert "az storage" not in text
    assert "${{ secrets." not in text.lower()


def test_postgresql_alert_validation_is_isolated_reversible_and_uses_builtin_metric() -> None:
    workflow_text = POSTGRES_SIMULATION_WORKFLOW_PATH.read_text(encoding="utf-8")
    workflow = yaml.safe_load(workflow_text)
    template = POSTGRES_VALIDATION_TEMPLATE_PATH.read_text(encoding="utf-8")
    job = workflow["jobs"]["simulate"]

    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "production"
    assert "RECOVERY_RESOURCE_GROUP: ${{ vars.AZURE_RECOVERY_RESOURCE_GROUP }}" in workflow_text
    assert 'test "$RECOVERY_RESOURCE_GROUP" != "$RESOURCE_GROUP"' in workflow_text
    assert "az deployment group create" in workflow_text
    assert "infra/azure/postgresql-alert-validation.bicep" in workflow_text
    assert "az postgres flexible-server stop" in workflow_text
    assert "az postgres flexible-server start" in workflow_text
    assert "az postgres flexible-server delete" in workflow_text
    assert (
        '--name "$VALIDATION_SERVER" \\\n'
        "            --output none\n\n"
        "          for attempt in $(seq 1 48)"
    ) in workflow_text
    assert "trap cleanup EXIT" in workflow_text
    assert "is_db_alive" in workflow_text
    assert "awk -v value=" in workflow_text
    assert workflow_text.count("awk -v value=") == 3
    assert 'test "${DB_ALIVE:-}" = "1"' not in workflow_text
    assert "ALERT_RESOLVED=true" in workflow_text
    assert 'monitorCondition == "Fired"' in workflow_text
    assert 'monitorCondition == "Resolved"' in workflow_text
    assert "fired-postgresql-validation-alert.json" in workflow_text
    assert "resolved-postgresql-validation-alert.json" in workflow_text
    assert "Microsoft.AlertsManagement/alerts" in workflow_text
    assert "az postgres flexible-server restore" not in workflow_text
    assert "az storage" not in workflow_text
    assert "az keyvault" not in workflow_text
    assert "database-url" not in workflow_text
    assert "${{ secrets." not in workflow_text.lower()

    assert "Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01" in template
    assert "Microsoft.Insights/metricAlerts@2018-03-01" in template
    assert "publicNetworkAccess: 'Disabled'" in template
    assert "metricName: 'is_db_alive'" in template
    assert "operator: 'LessThan'" in template
    assert "threshold: 1" in template
    assert "timeAggregation: 'Average'" in template
    assert "evaluationFrequency: 'PT5M'" in template
    assert "windowSize: 'PT15M'" in template
    assert "autoMitigate: true" in template
    assert "actions: []" in template
    assert "@secure()" in template


def test_financial_budget_is_scoped_approved_and_has_no_external_notification_channel() -> None:
    template = FINANCIAL_BUDGET_TEMPLATE_PATH.read_text(encoding="utf-8")
    access_template = FINANCIAL_BUDGET_ACCESS_PATH.read_text(encoding="utf-8")

    assert "targetScope = 'resourceGroup'" in template
    assert "Microsoft.Consumption/budgets@2023-05-01" in template
    assert "name: 'usiedu-monthly-budget'" in template
    assert "amount: 30" in template
    assert "timeGrain: 'Monthly'" in template
    assert "category: 'Cost'" in template
    assert "notifications:" not in template
    assert "contactEmails" not in template
    assert "contactGroups" not in template
    assert "contactRoles" not in template
    assert "webhook" not in template.lower()
    assert "teams" not in template.lower()

    assert "targetScope = 'resourceGroup'" in access_template
    assert "434105ed-43f6-45c7-a02f-909b2ba83430" in access_template
    assert "Cost Management Contributor" not in access_template
    assert "b24988ac-6180-42a0-ab88-20f7382dd24c" not in access_template


def test_financial_budget_workflows_are_manual_protected_and_deduplicate_issues() -> None:
    deploy_text = FINANCIAL_BUDGET_DEPLOY_WORKFLOW_PATH.read_text(encoding="utf-8")
    deploy_workflow = yaml.safe_load(deploy_text)
    report_text = FINANCIAL_BUDGET_REPORT_WORKFLOW_PATH.read_text(encoding="utf-8")
    report_workflow = yaml.safe_load(report_text)

    deploy_job = deploy_workflow["jobs"]["configure"]
    assert set(deploy_workflow["on"]) == {"workflow_dispatch"}
    assert deploy_workflow["permissions"] == {"contents": "read", "id-token": "write"}
    assert deploy_job["if"] == "github.ref == 'refs/heads/main'"
    assert deploy_job["environment"] == "production"
    assert "infra/azure/financial-budget.bicep" in deploy_text
    assert "az deployment group create" in deploy_text
    assert "BUDGET_START_DATE" in deploy_text
    assert "BRL" in deploy_text
    assert "notification_count" in deploy_text
    assert "issue_thresholds" in deploy_text
    assert "${{ secrets." not in deploy_text.lower()

    report_job = report_workflow["jobs"]["report"]
    assert set(report_workflow["on"]) == {"workflow_dispatch"}
    assert report_workflow["permissions"] == {
        "contents": "read",
        "id-token": "write",
        "issues": "write",
    }
    assert report_job["if"] == "github.ref == 'refs/heads/main'"
    assert report_job["environment"] == "production"
    assert "Microsoft.Consumption/budgets" in report_text
    assert "azure-financial-alert" in report_text
    assert "80" in report_text
    assert "100" in report_text
    assert "spend * 100 >= budget * threshold" in report_text
    assert "gh issue list" in report_text
    assert "gh issue create" in report_text
    assert "gh issue comment" in report_text
    assert "BRL" in report_text
    assert "webhook" not in report_text.lower()
    assert "teams" not in report_text.lower()
    assert "${{ secrets." not in report_text.lower()
