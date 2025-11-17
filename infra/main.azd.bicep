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

@description('AAD tenant ID to use for Entra ID authentication. Empty to use the current tenant.')
param aadTenantId string = ''

@description('Client ID of the frontend/public client application requesting tokens. Leave empty to create/manage via hooks.')
param aadFrontendClientId string = ''

@description('App ID URI (audience) for the protected API. Leave empty to skip auth configuration.')
param aadApiAudience string = ''

@description('Allowed e-mail domain for authenticated users.')
param allowedEmailDomain string = 'microsoft.com'

@description('String flag read from azd env that determines whether backend auth is disabled.')
param disableAuthSetting string = 'false'

@description('Enable fully private networking between Container Apps and Cosmos DB (VNet + private endpoint).')
param secureCosmosConnectivity bool = true

@description('CIDR for the secure VNet when secureCosmosConnectivity is enabled.')
param vnetAddressPrefix string = '10.90.0.0/16'

@description('CIDR for the Container Apps infrastructure subnet when secureCosmosConnectivity is enabled (must be /23 or larger).')
param containerAppsSubnetPrefix string = '10.90.0.0/23'

@description('CIDR for the private endpoint subnet when secureCosmosConnectivity is enabled.')
param privateEndpointSubnetPrefix string = '10.90.2.0/24'

@description('Optional Entra ID object ID for a developer that should get Cosmos DB data-plane roles in secure mode.')
param localDeveloperObjectId string = ''

var effectiveTenantId = !empty(aadTenantId) ? aadTenantId : tenant().tenantId
var authDisabled = toLower(disableAuthSetting) == 'true'
var secureCosmos = secureCosmosConnectivity

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

// Network resources for secure deployments
module network './modules/network.bicep' = if (secureCosmos) {
  scope: rg
  name: 'network-deployment'
  params: {
    location: location
    baseName: baseName
    environmentName: environmentName
    tags: tags
    addressPrefix: vnetAddressPrefix
    containerAppsSubnetPrefix: containerAppsSubnetPrefix
    privateEndpointSubnetPrefix: privateEndpointSubnetPrefix
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
    enablePrivateEndpoint: secureCosmos
    privateEndpointSubnetId: secureCosmos ? network!.outputs.privateEndpointSubnetId : ''
    privateDnsZoneId: secureCosmos ? network!.outputs.privateDnsZoneId : ''
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
    infrastructureSubnetId: secureCosmos ? network!.outputs.containerAppsSubnetId : ''
  }
}

// Managed identity for secure Container Apps deployment
module appIdentity './modules/managed-identity.bicep' = if (secureCosmos) {
  scope: rg
  name: 'app-identity'
  params: {
    location: location
    name: '${baseName}-apps-mi'
    tags: tags
  }
}

// Cosmos DB data-plane roles for managed identity
module appCosmosRoles './modules/cosmos-roles.bicep' = if (secureCosmos) {
  scope: rg
  name: 'app-cosmos-roles'
  params: {
    cosmosDbAccountName: cosmosdb.outputs.accountName
    principalId: appIdentity!.outputs.principalId
    roleAssignmentSalt: 'app'
  }
}

// Optional Cosmos DB role assignment for a developer
module devCosmosRoles './modules/cosmos-roles.bicep' = if (secureCosmos && !empty(localDeveloperObjectId)) {
  scope: rg
  name: 'developer-cosmos-roles'
  params: {
    cosmosDbAccountName: cosmosdb.outputs.accountName
    principalId: localDeveloperObjectId
    roleAssignmentSalt: 'localdev'
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
    cosmosDbKey: secureCosmos ? '' : cosmosdb.outputs.primaryKey
    cosmosDbName: cosmosdb.outputs.databaseName
    cosmosContainerName: cosmosdb.outputs.agentStateContainer
    useCosmosManagedIdentity: secureCosmos
    userAssignedIdentityResourceId: secureCosmos ? appIdentity!.outputs.resourceId : ''
    userAssignedIdentityClientId: secureCosmos ? appIdentity!.outputs.clientId : ''
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
    cosmosDbEndpoint: cosmosdb.outputs.endpoint
    cosmosDbName: cosmosdb.outputs.databaseName
    cosmosStateContainerName: cosmosdb.outputs.agentStateContainer
    cosmosDbKey: secureCosmos ? '' : cosmosdb.outputs.primaryKey
    useCosmosManagedIdentity: secureCosmos
    userAssignedIdentityResourceId: secureCosmos ? appIdentity!.outputs.resourceId : ''
    userAssignedIdentityClientId: secureCosmos ? appIdentity!.outputs.clientId : ''
    azureOpenAIEndpoint: openai.outputs.endpoint
    azureOpenAIKey: openai.outputs.key
    azureOpenAIDeploymentName: openai.outputs.chatDeploymentName
    azureOpenAIEmbeddingDeploymentName: openai.outputs.embeddingDeploymentName
    mcpServiceUrl: mcpService.outputs.serviceUrl
    imageName: appImageName
    tags: tags
    aadTenantId: effectiveTenantId
    aadClientId: aadFrontendClientId
    aadApiAudience: aadApiAudience
    disableAuth: authDisabled
    allowedEmailDomain: allowedEmailDomain
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
output AZURE_COSMOS_CONTAINER_NAME string = cosmosdb.outputs.agentStateContainer

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
