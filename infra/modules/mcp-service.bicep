// MCP Service Container App
param location string
param baseName string
param environmentName string
param containerAppsEnvironmentId string
param containerRegistryName string
param cosmosDbEndpoint string
@secure()
param cosmosDbKey string
param cosmosDbName string
param tags object

@description('Container image tag')
param imageTag string = 'latest'

@description('Full container image name from azd')
param imageName string = ''

var mcpServiceName = '${baseName}-mcp'
var containerImage = !empty(imageName) ? imageName : '${containerRegistryName}.azurecr.io/mcp-service:${imageTag}'
var azdTags = union(tags, {
  'azd-service-name': 'mcp'
  'azd-service-type': 'containerapp'
})

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource mcpService 'Microsoft.App/containerApps@2023-05-01' = {
  name: mcpServiceName
  location: location
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.listCredentials().username
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'cosmosdb-key'
          value: cosmosDbKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp-service'
          image: containerImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'COSMOSDB_ENDPOINT'
              value: cosmosDbEndpoint
            }
            {
              name: 'COSMOSDB_KEY'
              secretRef: 'cosmosdb-key'
            }
            {
              name: 'COSMOS_DB_NAME'
              value: cosmosDbName
            }
            {
              name: 'COSMOS_CONTAINER_NAME'
              value: 'workshop_agent_state_store'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
  tags: azdTags
}

output serviceUrl string = 'https://${mcpService.properties.configuration.ingress.fqdn}/mcp'
output serviceName string = mcpService.name
output fqdn string = mcpService.properties.configuration.ingress.fqdn
