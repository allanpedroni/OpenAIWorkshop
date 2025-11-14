// Azure Container Registry
param location string
param baseName string
param environmentName string
param tags object

@description('Container Registry SKU')
@allowed(['Basic', 'Standard', 'Premium'])
param sku string = 'Basic'

var acrName = replace('${baseName}${environmentName}acr', '-', '')

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: acrName
  location: location
  sku: {
    name: sku
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
    networkRuleBypassOptions: 'AzureServices'
  }
  tags: tags
}

output registryName string = containerRegistry.name
output loginServer string = containerRegistry.properties.loginServer
output registryId string = containerRegistry.id
