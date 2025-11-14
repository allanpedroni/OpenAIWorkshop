// Main infrastructure deployment for OpenAI Workshop
// Deploys: Azure OpenAI, Cosmos DB, Container Apps (MCP + Application)

targetScope = 'subscription'

@description('Azure region for all resources')
param location string = 'eastus2'

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environmentName string = 'dev'

@description('Base name for all resources')
param baseName string = 'openai-workshop'

@description('Tags to apply to all resources')
param tags object = {
  Environment: environmentName
  Application: 'OpenAI-Workshop'
  ManagedBy: 'Bicep'
}

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${baseName}-${environmentName}-rg'
  location: location
  tags: tags
}

// Azure OpenAI Service
module openai 'modules/openai.bicep' = {
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
module cosmosdb 'modules/cosmosdb.bicep' = {
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
module acr 'modules/container-registry.bicep' = {
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
module logAnalytics 'modules/log-analytics.bicep' = {
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
module containerAppsEnv 'modules/container-apps-environment.bicep' = {
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
module mcpService 'modules/mcp-service.bicep' = {
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
    tags: tags
  }
}

// Application (Backend + Frontend) Container App
module application 'modules/application.bicep' = {
  scope: rg
  name: 'application-deployment'
  params: {
    location: location
    baseName: baseName
    environmentName: environmentName
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    containerRegistryName: acr.outputs.registryName
    azureOpenAIEndpoint: openai.outputs.endpoint
    azureOpenAIKey: openai.outputs.key
    azureOpenAIDeploymentName: openai.outputs.chatDeploymentName
    mcpServiceUrl: mcpService.outputs.serviceUrl
    cosmosDbEndpoint: cosmosdb.outputs.endpoint
    cosmosDbKey: cosmosdb.outputs.primaryKey
    cosmosDbName: cosmosdb.outputs.databaseName
    tags: tags
  }
}

// Outputs
output resourceGroupName string = rg.name
output location string = location
output azureOpenAIEndpoint string = openai.outputs.endpoint
output cosmosDbEndpoint string = cosmosdb.outputs.endpoint
output containerRegistryName string = acr.outputs.registryName
output mcpServiceUrl string = mcpService.outputs.serviceUrl
output applicationUrl string = application.outputs.applicationUrl
output containerAppsEnvironmentId string = containerAppsEnv.outputs.environmentId
