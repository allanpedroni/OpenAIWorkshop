// Main infrastructure deployment for OpenAI Workshop (azd compatible)
// Deploys: Azure OpenAI, Cosmos DB, Container Apps (MCP + Application)

targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('MCP service container image')
param mcpImageName string = ''

@description('Application container image')
param appImageName string = ''

// Tags to apply to all resources
var tags = {
  'azd-env-name': environmentName
  Application: 'OpenAI-Workshop'
  ManagedBy: 'azd'
}

// Generate a unique token to be used in naming resources
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var baseName = 'aiws-${resourceToken}'

// Deterministic service names for Container Apps (used by azd deploy)
var mcpServiceName = '${baseName}-mcp'
var appServiceName = '${baseName}-app'

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

// Azure OpenAI Service
module openai './modules/openai.bicep' = {
  scope: rg
  name: 'openai-deployment'
  params: {
    location: location
    baseName: baseName
    environmentName: environmentName
    tags: tags
  }
}

// Cosmos DB with containers
module cosmosdb './modules/cosmosdb.bicep' = {
  scope: rg
  name: 'cosmosdb-deployment'
  params: {
    location: location
    baseName: baseName
    environmentName: environmentName
    tags: tags
  }
}

// Container Registry
module acr './modules/container-registry.bicep' = {
  scope: rg
  name: 'acr-deployment'
  params: {
    location: location
    baseName: baseName
    environmentName: environmentName
    tags: tags
  }
}

// Log Analytics Workspace (for Container Apps)
module logAnalytics './modules/log-analytics.bicep' = {
  scope: rg
  name: 'logs-deployment'
  params: {
    location: location
    baseName: baseName
    environmentName: environmentName
    tags: tags
  }
}

// Container Apps Environment
module containerAppsEnv './modules/container-apps-environment.bicep' = {
  scope: rg
  name: 'container-apps-env-deployment'
  params: {
    location: location
    baseName: baseName
    environmentName: environmentName
    logAnalyticsWorkspaceId: logAnalytics.outputs.workspaceId
    tags: tags
  }
}

// MCP Service Container App
module mcpService './modules/mcp-service.bicep' = {
  scope: rg
  name: 'mcp-service-deployment'
  params: {
    location: location
    baseName: baseName
    environmentName: environmentName
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    containerRegistryName: acr.outputs.registryName
    cosmosDbEndpoint: cosmosdb.outputs.endpoint
    cosmosDbKey: cosmosdb.outputs.primaryKey
    cosmosDbName: cosmosdb.outputs.databaseName
    imageName: mcpImageName
    tags: tags
  }
}

// Application (Backend + Frontend) Container App
// Application Container
module application './modules/application.bicep' = {
  scope: rg
  name: 'application-deployment'
  params: {
    location: location
    baseName: baseName
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    containerRegistryName: acr.outputs.registryName
    azureOpenAIEndpoint: openai.outputs.endpoint
    azureOpenAIKey: openai.outputs.key
    azureOpenAIDeploymentName: openai.outputs.chatDeploymentName
    azureOpenAIEmbeddingDeploymentName: openai.outputs.embeddingDeploymentName
    mcpServiceUrl: mcpService.outputs.serviceUrl
    imageName: appImageName
    tags: tags
  }
}

// Outputs for azd
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = rg.name

output AZURE_OPENAI_ENDPOINT string = openai.outputs.endpoint
output AZURE_OPENAI_CHAT_DEPLOYMENT string = openai.outputs.chatDeploymentName
output AZURE_OPENAI_EMBEDDING_DEPLOYMENT string = openai.outputs.embeddingDeploymentName

output AZURE_COSMOS_ENDPOINT string = cosmosdb.outputs.endpoint
output AZURE_COSMOS_DATABASE_NAME string = cosmosdb.outputs.databaseName

output AZURE_CONTAINER_REGISTRY_NAME string = acr.outputs.registryName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.outputs.loginServer

output AZURE_CONTAINER_APPS_ENVIRONMENT_ID string = containerAppsEnv.outputs.environmentId

// Service-specific outputs for azd deploy
// ALWAYS return deterministic names (not from module outputs)
output SERVICE_MCP_NAME string = mcpServiceName
output SERVICE_APP_NAME string = appServiceName

// User-friendly outputs (can be empty if not deployed)
output MCP_SERVICE_URL string = mcpService.?outputs.?serviceUrl ?? ''
output MCP_SERVICE_NAME string = mcpServiceName

output APPLICATION_URL string = application.?outputs.?applicationUrl ?? ''
output APPLICATION_NAME string = appServiceName
