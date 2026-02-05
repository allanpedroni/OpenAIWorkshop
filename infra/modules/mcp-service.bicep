// MCP Service Container App
param location string
param baseName string
param environmentName string
param containerAppsEnvironmentId string
param containerRegistryName string
param cosmosDbEndpoint string
@secure()
param cosmosDbKey string = ''
param cosmosDbName string
@description('Cosmos DB container name that stores MCP state')
param cosmosContainerName string = 'workshop_agent_state_store'
@description('Set to true to rely on managed identity for Cosmos DB access')
param useCosmosManagedIdentity bool = false
@description('Optional user-assigned managed identity resource ID attached to the MCP container app')
param userAssignedIdentityResourceId string = ''
@description('Client ID for the user-assigned managed identity attached to the MCP container app')
param userAssignedIdentityClientId string = ''
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
var cosmosSecrets = (!useCosmosManagedIdentity && !empty(cosmosDbKey)) ? [
  {
    name: 'cosmosdb-key'
    value: cosmosDbKey
  }
] : []

var cosmosEnvSettings = concat([
  {
    name: 'COSMOSDB_ENDPOINT'
    value: cosmosDbEndpoint
  }
  {
    name: 'COSMOS_DB_NAME'
    value: cosmosDbName
  }
  {
    name: 'COSMOS_CONTAINER_NAME'
    value: cosmosContainerName
  }
  {
    name: 'COSMOS_USE_MANAGED_IDENTITY'
    value: string(useCosmosManagedIdentity)
  }
], (!useCosmosManagedIdentity && !empty(cosmosDbKey)) ? [
  {
    name: 'COSMOSDB_KEY'
    secretRef: 'cosmosdb-key'
  }
] : [])
var managedIdentityEnv = !empty(userAssignedIdentityClientId) ? [
  {
    name: 'AZURE_CLIENT_ID'
    value: userAssignedIdentityClientId
  }
  {
    name: 'MANAGED_IDENTITY_CLIENT_ID'
    value: userAssignedIdentityClientId
  }
] : []

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource mcpService 'Microsoft.App/containerApps@2023-05-01' = {
  name: mcpServiceName
  location: location
  identity: (useCosmosManagedIdentity && !empty(userAssignedIdentityResourceId)) ? {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  } : null
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
      secrets: concat([
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ], cosmosSecrets)
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
          env: concat(cosmosEnvSettings, managedIdentityEnv)
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
output internalUrl string = 'http://${mcpService.name}/mcp'
output serviceName string = mcpService.name
output fqdn string = mcpService.properties.configuration.ingress.fqdn
