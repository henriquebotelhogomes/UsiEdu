@description('Object ID da identidade OIDC que executa o exercício de recuperação.')
param deploymentPrincipalId string

@description('Nome do PostgreSQL de produção usado apenas como origem do restore.')
param postgresServerName string

@description('Nome da conta de armazenamento que contém o share Qdrant de produção.')
param storageAccountName string

var storageAccountContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '17d1049b-9a84-46fb-8f53-869881c3d3ab'
)
var storageAccountKeyOperatorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '81a9662b-bebf-436f-a333-f67b29880f12'
)
var postgresRestoreSourceRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  guid(subscription().id, 'usiedu-postgres-restore-source-operator')
)

resource postgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' existing = {
  name: postgresServerName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' existing = {
  name: storageAccountName
}

resource deploymentPostgresRestoreSourceOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(postgresServer.id, deploymentPrincipalId, postgresRestoreSourceRoleDefinitionId)
  scope: postgresServer
  properties: {
    principalId: deploymentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: postgresRestoreSourceRoleDefinitionId
  }
}

resource deploymentStorageContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, deploymentPrincipalId, storageAccountContributorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: deploymentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageAccountContributorRoleDefinitionId
  }
}

resource deploymentStorageKeyOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, deploymentPrincipalId, storageAccountKeyOperatorRoleDefinitionId)
  scope: storageAccount
  properties: {
    principalId: deploymentPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageAccountKeyOperatorRoleDefinitionId
  }
}
