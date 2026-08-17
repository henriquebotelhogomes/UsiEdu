targetScope = 'resourceGroup'

@description('Object ID da identidade OIDC que configura e consulta o orçamento financeiro.')
param deploymentPrincipalId string

var costManagementContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '434105ed-43f6-45c7-a02f-909b2ba83430'
)

resource deploymentCostManagementContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, deploymentPrincipalId, costManagementContributorRoleDefinitionId)
  scope: resourceGroup()
  properties: {
    principalId: deploymentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: costManagementContributorRoleDefinitionId
  }
}
