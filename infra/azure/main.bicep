@description('Prefixo curto para os recursos. Use letras minúsculas, números e hífen.')
param namePrefix string = 'usiedu'

param location string = resourceGroup().location

@description('Imagem já publicada da API, incluindo tag imutável.')
param apiImage string

@description('Imagem já publicada do frontend, incluindo tag imutável.')
param frontendImage string

@description('Servidor de login do Azure Container Registry (opcional se imagem pública).')
param registryLoginServer string = ''

@secure()
param registryUsername string = ''

@secure()
param registryPassword string = ''

@secure()
param jwtSecret string

@secure()
param opencodeApiKey string

@secure()
param langsmithApiKey string

@description('URL do endpoint OpenCode Go compatível com OpenAI.')
param opencodeBaseUrl string = 'https://opencode.ai/zen/go/v1'

param routerModel string = 'deepseek-v4-flash'
param agentModel string = 'kimi-k2.7-code'

@description('Nome globalmente único da conta de armazenamento.')
param storageAccountName string = toLower('usiedu${uniqueString(subscription().id, resourceGroup().id)}')

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey
      }
    }
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    minimumTlsVersion: 'TLS1_2'
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource qdrantShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'qdrant'
  properties: {
    accessTier: 'TransactionOptimized'
  }
}

resource apiShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-05-01' = {
  parent: fileService
  name: 'apidata'
  properties: {
    accessTier: 'TransactionOptimized'
  }
}

resource qdrantStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: environment
  name: 'qdrant-data'
  properties: {
    azureFile: {
      accountKey: storageAccount.listKeys().keys[0].value
      accountName: storageAccount.name
      accessMode: 'ReadWrite'
      shareName: qdrantShare.name
    }
  }
}

resource apiStorage 'Microsoft.App/managedEnvironments/storages@2024-03-01' = {
  parent: environment
  name: 'api-data'
  properties: {
    azureFile: {
      accountKey: storageAccount.listKeys().keys[0].value
      accountName: storageAccount.name
      accessMode: 'ReadWrite'
      shareName: apiShare.name
    }
  }
}

resource qdrantApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-qdrant'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: false
        targetPort: 6333
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'qdrant'
          image: 'qdrant/qdrant:v1.14.1'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          volumeMounts: [
            {
              volumeName: 'qdrant-data'
              mountPath: '/qdrant/storage'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
      volumes: [
        {
          name: 'qdrant-data'
          storageType: 'AzureFile'
          storageName: qdrantStorage.name
        }
      ]
    }
  }
}

resource apiApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: empty(registryLoginServer) ? [
        {
          name: 'jwt-secret'
          value: jwtSecret
        }
        {
          name: 'opencode-api-key'
          value: opencodeApiKey
        }
        {
          name: 'langsmith-api-key'
          value: langsmithApiKey
        }
      ] : [
        {
          name: 'registry-password'
          value: registryPassword
        }
        {
          name: 'jwt-secret'
          value: jwtSecret
        }
        {
          name: 'opencode-api-key'
          value: opencodeApiKey
        }
        {
          name: 'langsmith-api-key'
          value: langsmithApiKey
        }
      ]
      registries: empty(registryLoginServer) ? [] : [
        {
          server: registryLoginServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      ingress: {
        external: false
        targetPort: 8000
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'api'
          image: apiImage
          resources: {
            cpu: json('2.0')
            memory: '4Gi'
          }
          volumeMounts: [
            {
              volumeName: 'api-data'
              mountPath: '/app/data'
            }
          ]
          env: [
            {
              name: 'USIEDU_ENV'
              value: 'prod'
            }
            {
              name: 'JWT_SECRET'
              secretRef: 'jwt-secret'
            }
            {
              name: 'OPENCODE_GO_API_KEY'
              secretRef: 'opencode-api-key'
            }
            {
              name: 'OPENCODE_GO_BASE_URL'
              value: opencodeBaseUrl
            }
            {
              name: 'USIEDU_LLM_PROVIDER'
              value: 'opencode-go'
            }
            {
              name: 'USIEDU_ROUTER_MODEL'
              value: routerModel
            }
            {
              name: 'USIEDU_AGENT_MODEL'
              value: agentModel
            }
            {
              name: 'LANGSMITH_TRACING'
              value: 'true'
            }
            {
              name: 'LANGSMITH_API_KEY'
              secretRef: 'langsmith-api-key'
            }
            {
              name: 'LANGSMITH_PROJECT'
              value: '${namePrefix}-pilot'
            }
            {
              name: 'LANGCHAIN_TRACING_V2'
              value: 'true'
            }
            {
              name: 'LANGCHAIN_API_KEY'
              secretRef: 'langsmith-api-key'
            }
            {
              name: 'LANGCHAIN_PROJECT'
              value: '${namePrefix}-pilot'
            }
            {
              name: 'QDRANT_URL'
              value: 'http://${qdrantApp.name}:80'
            }
            {
              name: 'USIEDU_FEEDBACK_DB'
              value: '/app/data/usiedu_feedback.db'
            }
            {
              name: 'USIEDU_CACHE_DB'
              value: '/app/data/usiedu_cache.db'
            }
            {
              name: 'USIEDU_CACHE_ENABLED'
              value: 'true'
            }
            {
              name: 'USIEDU_CACHE_SIMILARITY'
              value: '0.97'
            }
            {
              name: 'USIEDU_CACHE_TTL_DAYS'
              value: '30'
            }
            {
              name: 'USIEDU_RATE_CHAT'
              value: '10/minute'
            }
            {
              name: 'USIEDU_RATE_LOGIN'
              value: '5/minute'
            }
            {
              name: 'USIEDU_RATE_FEEDBACK'
              value: '30/minute'
            }
            {
              name: 'USIEDU_CORS_ORIGINS'
              value: 'https://${namePrefix}-frontend.${environment.properties.defaultDomain}'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
      volumes: [
        {
          name: 'api-data'
          storageType: 'AzureFile'
          storageName: apiStorage.name
        }
      ]
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-frontend'
  location: location
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      secrets: empty(registryLoginServer) ? [] : [
        {
          name: 'registry-password'
          value: registryPassword
        }
      ]
      registries: empty(registryLoginServer) ? [] : [
        {
          server: registryLoginServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: frontendImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'UPSTREAM_API_URL'
              value: 'http://${apiApp.name}'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

resource ingestJob 'Microsoft.App/jobs@2024-03-01' = {
  name: '${namePrefix}-ingest'
  location: location
  properties: {
    environmentId: environment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 1800
      replicaRetryLimit: 0
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
      secrets: empty(registryLoginServer) ? [] : [
        {
          name: 'registry-password'
          value: registryPassword
        }
      ]
      registries: empty(registryLoginServer) ? [] : [
        {
          server: registryLoginServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'ingest'
          image: apiImage
          command: [
            'python'
            'scripts/ingest_knowledge_base.py'
          ]
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'QDRANT_URL'
              value: 'http://${qdrantApp.name}:80'
            }
          ]
        }
      ]
    }
  }
}

output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output resourceGroup string = resourceGroup().name
output ingestJobName string = ingestJob.name
