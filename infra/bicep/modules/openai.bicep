// Azure OpenAI Service deployment
param location string
param baseName string
param environmentName string
param tags object

@description('Azure OpenAI SKU')
param sku string = 'S0'

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

resource openAI 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAIName
  location: location
  kind: 'OpenAI'
  sku: {
    name: sku
  }
  properties: {
    customSubDomainName: openAIName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
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

output endpoint string = openAI.properties.endpoint
output key string = openAI.listKeys().key1
output name string = openAI.name
output chatDeploymentName string = deployments[0].name
output embeddingDeploymentName string = deployments[1].name
