targetScope = 'subscription'

@description('Grupo de recursos que contém o PostgreSQL de origem do restore.')
param sourceResourceGroupName string

resource postgresRestoreSourceRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(subscription().id, 'usiedu-postgres-restore-source-operator')
  properties: {
    roleName: 'UsiEdu PostgreSQL Restore Source Operator'
    description: 'Permite somente ler e vincular um PostgreSQL como origem de restore isolado.'
    type: 'CustomRole'
    permissions: [
      {
        actions: [
          'Microsoft.DBforPostgreSQL/flexibleServers/read'
          'Microsoft.DBforPostgreSQL/flexibleServers/write'
        ]
        notActions: []
        dataActions: []
        notDataActions: []
      }
    ]
    assignableScopes: [resourceId('Microsoft.Resources/resourceGroups', sourceResourceGroupName)]
  }
}

resource environmentStorageOperatorRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: guid(subscription().id, 'usiedu-container-apps-environment-storage-operator')
  properties: {
    roleName: 'UsiEdu Container Apps Environment Storage Operator'
    description: 'Permite somente gerenciar mounts Azure Files efemeros do ambiente gerenciado.'
    type: 'CustomRole'
    permissions: [
      {
        actions: [
          'microsoft.app/managedenvironments/storages/read'
          'microsoft.app/managedenvironments/storages/write'
          'microsoft.app/managedenvironments/storages/delete'
        ]
        notActions: []
        dataActions: []
        notDataActions: []
      }
    ]
    assignableScopes: [resourceId('Microsoft.Resources/resourceGroups', sourceResourceGroupName)]
  }
}
