// Application Container App (Backend FastAPI + Frontend Node)
@description('Azure region for deployment')
param location string

@description('Base name for resources')
param baseName string

@description('Container Apps Environment resource ID')
param containerAppsEnvironmentId string

@description('Container Registry name')
param containerRegistryName string

@description('Cosmos DB endpoint for agent state persistence')
param cosmosDbEndpoint string = ''

@description('Cosmos DB database name for agent state persistence')
param cosmosDbName string = ''

@description('Cosmos DB container name for agent state persistence')
param cosmosStateContainerName string = ''

@description('Cosmos DB primary key (used when managed identity is disabled)')
@secure()
param cosmosDbKey string = ''

@description('Set to true to rely on managed identity for Cosmos DB access')
param useCosmosManagedIdentity bool = false

@description('Optional user-assigned managed identity resource ID attached to the container app')
param userAssignedIdentityResourceId string = ''

@description('Client ID for the user-assigned managed identity attached to the container app')
param userAssignedIdentityClientId string = ''

@description('Azure OpenAI endpoint URL')
param azureOpenAIEndpoint string

@description('Azure OpenAI deployment name')
param azureOpenAIDeploymentName string

@description('Azure OpenAI embedding deployment name')
param azureOpenAIEmbeddingDeploymentName string

@description('MCP service URL')
param mcpServiceUrl string

@description('Resource tags')
param tags object

@description('AAD tenant ID used for authentication enforcement. Empty to fallback to the current tenant context.')
param aadTenantId string = ''

@description('Public client ID requesting tokens (frontend).')
param aadClientId string = ''

@description('App ID URI (audience) for the protected API.')
param aadApiAudience string = ''

@description('Whether to disable auth in the backend.')
param disableAuth bool = true

@description('Allowed e-mail domain for authenticated users when auth is enabled.')
param allowedEmailDomain string = 'microsoft.com'

@description('Container image tag')
param imageTag string = 'latest'

@description('Full container image name from azd')
param imageName string = ''

@description('Environment name for naming convention')
param environmentName string = 'dev'

@description('Use placeholder image for initial deployment (before real image is pushed to ACR)')
param usePlaceholderImage bool = true

@description('Azure OpenAI API version')
param azureOpenAIApiVersion string = '2025-03-01-preview'

var appName = '${baseName}-app-${environmentName}'
// Use placeholder image for initial deployment - update-containers.yml will set the real image
var containerImage = !empty(imageName) ? imageName : (usePlaceholderImage ? 'mcr.microsoft.com/k8se/quickstart:latest' : '${containerRegistryName}.azurecr.io/backend-app:${imageTag}')
var azdTags = union(tags, {
  'azd-service-name': 'app'
  'azd-service-type': 'containerapp'
})
var effectiveTenantId = !empty(aadTenantId) ? aadTenantId : tenant().tenantId
var apiAudience = aadApiAudience
var aadAuthority = !empty(effectiveTenantId) ? '${environment().authentication.loginEndpoint}${effectiveTenantId}' : ''
var cosmosSecretEntries = (!useCosmosManagedIdentity && !empty(cosmosDbKey)) ? [
  {
    name: 'cosmosdb-key'
    value: cosmosDbKey
  }
] : []

var cosmosEndpointEnv = !empty(cosmosDbEndpoint) ? [
  {
    name: 'COSMOSDB_ENDPOINT'
    value: cosmosDbEndpoint
  }
] : []

var cosmosDbNameEnv = !empty(cosmosDbName) ? [
  {
    name: 'COSMOS_DB_NAME'
    value: cosmosDbName
  }
] : []

var cosmosContainerEnv = !empty(cosmosStateContainerName) ? [
  {
    name: 'COSMOS_CONTAINER_NAME'
    value: cosmosStateContainerName
  }
] : []

var cosmosKeyEnv = (!useCosmosManagedIdentity && !empty(cosmosDbKey)) ? [
  {
    name: 'COSMOSDB_KEY'
    secretRef: 'cosmosdb-key'
  }
] : []

var cosmosEnvSettings = concat(cosmosEndpointEnv, cosmosDbNameEnv, cosmosContainerEnv)
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

resource application 'Microsoft.App/containerApps@2023-05-01' = {
  name: appName
  location: location
  identity: empty(userAssignedIdentityResourceId) ? null : {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      ingress: {
        external: true
        targetPort: 3000
        transport: 'http'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          allowCredentials: true
        }
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
      ], cosmosSecretEntries)
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: containerImage
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/docs'
                port: 3000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
          env: concat([
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: azureOpenAIDeploymentName
            }
            {
              name: 'AZURE_AI_AGENT_MODEL_DEPLOYMENT_NAME'
              value: azureOpenAIDeploymentName
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT'
              value: azureOpenAIEmbeddingDeploymentName
            }
            {
              name: 'AZURE_OPENAI_EMB_DEPLOYMENT'
              value: azureOpenAIEmbeddingDeploymentName
            }
            {
              name: 'AZURE_OPENAI_API_VERSION'
              value: azureOpenAIApiVersion
            }
            {
              name: 'OPENAI_MODEL_NAME'
              value: 'gpt-5-chat'
            }
            {
              name: 'MCP_SERVER_URI'
              value: mcpServiceUrl
            }
          ], cosmosEnvSettings, cosmosKeyEnv, managedIdentityEnv, [
            {
              name: 'COSMOS_USE_MANAGED_IDENTITY'
              value: string(useCosmosManagedIdentity)
            }
            {
              name: 'DISABLE_AUTH'
              value: string(disableAuth)
            }
            {
              name: 'AGENT_MODULE'
              value: 'agents.agent_framework.single_agent'
            }
            {
              name: 'MAGENTIC_LOG_WORKFLOW_EVENTS'
              value: 'true'
            }
            {
              name: 'MAGENTIC_ENABLE_PLAN_REVIEW'
              value: 'true'
            }
            {
              name: 'MAGENTIC_MAX_ROUNDS'
              value: '10'
            }
            {
              name: 'HANDOFF_CONTEXT_TRANSFER_TURNS'
              value: '-1'
            }
            {
              name: 'AAD_TENANT_ID'
              value: effectiveTenantId
            }
            {
              name: 'TENANT_ID'
              value: effectiveTenantId
            }
            {
              name: 'CLIENT_ID'
              value: aadClientId
            }
            {
              name: 'AUTHORITY'
              value: aadAuthority
            }
            {
              name: 'MCP_API_AUDIENCE'
              value: apiAudience
            }
            {
              name: 'AAD_API_SCOPE'
              value: !empty(apiAudience) ? '${apiAudience}/user_impersonation' : ''
            }
            {
              name: 'ALLOWED_EMAIL_DOMAIN'
              value: allowedEmailDomain
            }
          ])
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '20'
              }
            }
          }
        ]
      }
    }
  }
  tags: azdTags
}

output applicationUrl string = 'https://${application.properties.configuration.ingress.fqdn}'
output applicationName string = application.name
output fqdn string = application.properties.configuration.ingress.fqdn
