targetScope = 'resourceGroup'

@description('Object ID da identidade OIDC que provisiona e consulta alertas.')
param deploymentPrincipalId string

@description('Nome do workspace Log Analytics que recebe os logs das Container Apps.')
param logAnalyticsWorkspaceName string

var monitoringContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '749f88d5-cbae-40b8-bcfc-e573ddc772fa'
)
var logAnalyticsReaderRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '73c42c96-874c-492b-b04d-ab87d138a893'
)

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource deploymentMonitoringContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, deploymentPrincipalId, monitoringContributorRoleDefinitionId)
  scope: resourceGroup()
  properties: {
    principalId: deploymentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: monitoringContributorRoleDefinitionId
  }
}

resource deploymentLogAnalyticsReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(logAnalyticsWorkspace.id, deploymentPrincipalId, logAnalyticsReaderRoleDefinitionId)
  scope: logAnalyticsWorkspace
  properties: {
    principalId: deploymentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: logAnalyticsReaderRoleDefinitionId
  }
}
