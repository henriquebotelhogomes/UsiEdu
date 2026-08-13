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
