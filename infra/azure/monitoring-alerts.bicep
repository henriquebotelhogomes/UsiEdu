@description('Nome do workspace Log Analytics que recebe os logs das Container Apps.')
param logAnalyticsWorkspaceName string

@description('Nome do servidor PostgreSQL existente a ser monitorado.')
param postgresServerName string

@description('Nome do job manual de ingestao existente a ser monitorado.')
param ingestJobName string

@description('Região dos recursos de monitoramento.')
param location string = resourceGroup().location

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' existing = {
  name: postgresServerName
}

var ingestJobFailureQuery = '''
  ContainerAppSystemLogs_CL
  | where TimeGenerated > ago(5m)
  | where JobName_s == '{ingestJobName}'
  | where Reason_s == 'BackoffLimitExceeded'
'''

resource containerAppTracebacksAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: 'usiedu-containerapp-tracebacks'
  location: location
  kind: 'LogAlert'
  properties: {
    autoMitigate: true
    checkWorkspaceAlertsStorageConfigured: false
    criteria: {
      allOf: [
        {
          failingPeriods: {
            minFailingPeriodsToAlert: 1
            numberOfEvaluationPeriods: 1
          }
          operator: 'GreaterThan'
          query: '''
            ContainerAppConsoleLogs_CL
            | where TimeGenerated > ago(5m)
            | where Stream_s == 'stderr'
            | where Log_s has 'Traceback'
          '''
          threshold: 0
          timeAggregation: 'Count'
        }
      ]
    }
    description: 'Erro de aplicacao com traceback nos logs de Container Apps.'
    displayName: 'UsiEdu Container Apps traceback'
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      logAnalyticsWorkspace.id
    ]
    severity: 2
    skipQueryValidation: false
    windowSize: 'PT5M'
  }
}

resource ingestJobFailureAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: 'usiedu-ingest-failed'
  location: location
  kind: 'LogAlert'
  properties: {
    autoMitigate: true
    checkWorkspaceAlertsStorageConfigured: false
    criteria: {
      allOf: [
        {
          failingPeriods: {
            minFailingPeriodsToAlert: 1
            numberOfEvaluationPeriods: 1
          }
          operator: 'GreaterThan'
          query: replace(ingestJobFailureQuery, '{ingestJobName}', ingestJobName)
          threshold: 0
          timeAggregation: 'Count'
        }
      ]
    }
    description: 'O job manual de ingestao excedeu o limite de tentativas.'
    displayName: 'UsiEdu ingest job failed'
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      logAnalyticsWorkspace.id
    ]
    severity: 2
    skipQueryValidation: false
    windowSize: 'PT5M'
  }
}

resource postgresAvailabilityAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: 'usiedu-postgresql-unavailable'
  location: 'global'
  properties: {
    actions: []
    autoMitigate: true
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          dimensions: []
          metricName: 'is_db_alive'
          metricNamespace: 'Microsoft.DBforPostgreSQL/flexibleServers'
          name: 'PostgreSQL unavailable'
          operator: 'LessThan'
          skipMetricValidation: false
          threshold: 1
          timeAggregation: 'Average'
        }
      ]
    }
    description: 'PostgreSQL indisponivel por pelo menos 15 minutos.'
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      postgresServer.id
    ]
    severity: 1
    targetResourceRegion: location
    targetResourceType: 'Microsoft.DBforPostgreSQL/flexibleServers'
    windowSize: 'PT15M'
  }
}

output containerAppTracebacksAlertName string = containerAppTracebacksAlert.name
output ingestJobFailureAlertName string = ingestJobFailureAlert.name
output postgresAvailabilityAlertName string = postgresAvailabilityAlert.name
