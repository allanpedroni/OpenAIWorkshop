// Azure OpenAI Service deployment
param location string
param baseName string
param environmentName string
param tags object

@description('Azure OpenAI SKU')
param sku string = 'S0'

@description('Principal ID to assign Cognitive Services OpenAI User role (for managed identity auth)')
param openAIUserPrincipalId string = ''

@description('Enable private endpoint (disables public network access)')
param enablePrivateEndpoint bool = false

@description('Model deployments to create')
param deployments array = [
  {
    name: 'gpt-5-chat'
    model: {
      format: 'OpenAI'
      name: 'gpt-5-chat'
      version: '2025-10-03'
    }
    sku: {
      name: 'GlobalStandard'
      capacity: 10
    }
  }
  {
    name: 'text-embedding-ada-002'
    model: {
      format: 'OpenAI'
      name: 'text-embedding-ada-002'
      version: '2'
    }
    sku: {
      name: 'GlobalStandard'
      capacity: 10
    }
  }
]

var openAIName = '${baseName}-${environmentName}-openai'

// Cognitive Services OpenAI User role definition ID
var cognitiveServicesOpenAIUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource openAI 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAIName
  location: location
  kind: 'OpenAI'
  sku: {
    name: sku
  }
  properties: {
    customSubDomainName: openAIName
    publicNetworkAccess: enablePrivateEndpoint ? 'Disabled' : 'Enabled'
    networkAcls: {
      defaultAction: enablePrivateEndpoint ? 'Deny' : 'Allow'
    }
  }
  tags: tags
}

@batchSize(1)
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = [for item in deployments: {
  parent: openAI
  name: item.name
  properties: {
    model: item.model
    raiPolicyName: null
  }
  sku: item.sku
}]

// Cognitive Services OpenAI User role assignment for managed identity authentication
// Allows inference API calls (chat completions, embeddings) without API keys
resource openAIUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(openAIUserPrincipalId)) {
  name: guid(openAI.id, openAIUserPrincipalId, cognitiveServicesOpenAIUserRoleId)
  scope: openAI
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleId)
    principalId: openAIUserPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output endpoint string = openAI.properties.endpoint
output name string = openAI.name
output resourceId string = openAI.id
output chatDeploymentName string = deployments[0].name
output embeddingDeploymentName string = deployments[1].name
