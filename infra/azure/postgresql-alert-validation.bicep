@description('Nome exclusivo do servidor PostgreSQL efemero usado somente na validacao do alerta.')
param validationServerName string

@description('Nome exclusivo da regra de alerta efemera.')
param validationAlertName string

@description('Senha efemera do administrador do servidor de validacao.')
@secure()
param administratorLoginPassword string

@description('Regiao do recurso isolado.')
param location string = resourceGroup().location

resource validationPostgresServer 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: validationServerName
  location: location
  tags: {
    purpose: 'postgresql-alert-validation'
    lifecycle: 'ephemeral'
  }
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    administratorLogin: 'alertvalidator'
    administratorLoginPassword: administratorLoginPassword
    version: '16'
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Disabled'
    }
  }
}

resource validationAvailabilityAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: validationAlertName
  location: 'global'
  tags: {
    purpose: 'postgresql-alert-validation'
    lifecycle: 'ephemeral'
  }
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
    description: 'Validacao isolada de indisponibilidade PostgreSQL por pelo menos 15 minutos.'
    enabled: true
    evaluationFrequency: 'PT5M'
    scopes: [
      validationPostgresServer.id
    ]
    severity: 1
    targetResourceRegion: location
    targetResourceType: 'Microsoft.DBforPostgreSQL/flexibleServers'
    windowSize: 'PT15M'
  }
}

output validationServerId string = validationPostgresServer.id
output validationAlertName string = validationAvailabilityAlert.name
