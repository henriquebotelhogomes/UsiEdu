@description('Nome do Container App efemero que monta o clone Qdrant.')
param appName string

@description('ID do ambiente gerenciado existente que pode acessar o Qdrant de origem.')
param managedEnvironmentId string

@description('Nome temporario do storage do ambiente que aponta para o clone Qdrant.')
param environmentStorageName string

@description('FQDN interno do Qdrant de origem.')
param sourceQdrantFqdn string

@description('Regiao do Container App efemero.')
param location string = resourceGroup().location

resource recoveryQdrantValidation 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  properties: {
    managedEnvironmentId: managedEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
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
        {
          name: 'validator'
          image: 'python:3.12.10-alpine3.21'
          command: [
            'sh'
            '-c'
            join([
              'python - <<PY'
              'import hashlib'
              'import json'
              'import os'
              'import time'
              'from urllib.request import urlopen'
              ''
              'def collections(url):'
              '    with urlopen(f"{url}/collections", timeout=10) as response:'
              '        payload = json.load(response)'
              '    return sorted(item["name"] for item in payload["result"]["collections"])'
              ''
              'for _ in range(60):'
              '    try:'
              '        with urlopen("http://127.0.0.1:6333/healthz", timeout=5):'
              '            break'
              '    except OSError:'
              '        time.sleep(5)'
              'else:'
              '    raise SystemExit("Recovered Qdrant health check did not become ready")'
              ''
              'source = collections(os.environ["SOURCE_QDRANT_URL"])'
              'recovery = collections("http://127.0.0.1:6333")'
              'source_hash = hashlib.sha256(chr(10).join(source).encode()).hexdigest()'
              'recovery_hash = hashlib.sha256(chr(10).join(recovery).encode()).hexdigest()'
              'result = {'
              '    "validated": source == recovery,'
              '    "source_collection_count": len(source),'
              '    "recovery_collection_count": len(recovery),'
              '    "source_collections_sha256": source_hash,'
              '    "recovery_collections_sha256": recovery_hash,'
              '}'
              'print("QDRANT_RECOVERY_VALIDATION=" + json.dumps(result, sort_keys=True), flush=True)'
              'if not result["validated"]:'
              '    raise SystemExit("Recovered Qdrant collection fingerprint does not match source")'
              'while True:'
              '    time.sleep(3600)'
              'PY'
            ], '\n')
          ]
          env: [
            {
              name: 'SOURCE_QDRANT_URL'
              value: 'https://${sourceQdrantFqdn}'
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
      volumes: [
        {
          name: 'qdrant-data'
          storageType: 'AzureFile'
          storageName: environmentStorageName
        }
      ]
    }
  }
}

output recoveryQdrantValidationName string = recoveryQdrantValidation.name
