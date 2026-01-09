@description('Azure region for networking resources')
param location string

@description('Base name applied to networking resources')
param baseName string

@description('Environment suffix for resource names')
param environmentName string

@description('Tags propagated to networking resources')
param tags object

@description('Address space for the virtual network')
param addressPrefix string = '10.10.0.0/16'

@description('Subnet CIDR for the Container Apps managed environment infrastructure subnet (must be at least /23)')
param containerAppsSubnetPrefix string = '10.10.0.0/23'

@description('Subnet CIDR for private endpoints (Cosmos DB, OpenAI, etc.)')
param privateEndpointSubnetPrefix string = '10.10.2.0/24'

@description('Enable private endpoints for Azure services')
param enablePrivateEndpoints bool = false

@description('Cosmos DB account ID for private endpoint')
param cosmosDbAccountId string = ''

@description('Azure OpenAI account ID for private endpoint')
param openAIAccountId string = ''

var vnetName = '${baseName}-${environmentName}-vnet'
var containerAppsSubnetName = 'containerapps-infra'
var privateEndpointSubnetName = 'private-endpoints'
var cosmosDnsZoneName = 'privatelink.documents.azure.com'
var openAIDnsZoneName = 'privatelink.openai.azure.com'
var cosmosDnsLinkName = '${vnetName}-cosmos-link'
var openAIDnsLinkName = '${vnetName}-openai-link'

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        addressPrefix
      ]
    }
    subnets: [
      {
        name: containerAppsSubnetName
        properties: {
          addressPrefix: containerAppsSubnetPrefix
          privateEndpointNetworkPolicies: 'Enabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: privateEndpointSubnetName
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
    ]
  }
}

// Cosmos DB Private DNS Zone
resource cosmosDnsZone 'Microsoft.Network/privateDnsZones@2018-09-01' = {
  name: cosmosDnsZoneName
  location: 'global'
  tags: tags
}

resource cosmosDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2018-09-01' = {
  parent: cosmosDnsZone
  name: cosmosDnsLinkName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

// OpenAI Private DNS Zone
resource openAIDnsZone 'Microsoft.Network/privateDnsZones@2018-09-01' = {
  name: openAIDnsZoneName
  location: 'global'
  tags: tags
}

resource openAIDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2018-09-01' = {
  parent: openAIDnsZone
  name: openAIDnsLinkName
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

// Cosmos DB Private Endpoint
resource cosmosPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-04-01' = if (enablePrivateEndpoints && cosmosDbAccountId != '') {
  name: '${baseName}-${environmentName}-cosmos-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[1].id
    }
    privateLinkServiceConnections: [
      {
        name: '${baseName}-${environmentName}-cosmos-psc'
        properties: {
          privateLinkServiceId: cosmosDbAccountId
          groupIds: [
            'Sql'
          ]
        }
      }
    ]
  }
}

resource cosmosPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-04-01' = if (enablePrivateEndpoints && cosmosDbAccountId != '') {
  parent: cosmosPrivateEndpoint
  name: 'cosmos-dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cosmos-config'
        properties: {
          privateDnsZoneId: cosmosDnsZone.id
        }
      }
    ]
  }
}

// OpenAI Private Endpoint
resource openAIPrivateEndpoint 'Microsoft.Network/privateEndpoints@2023-04-01' = if (enablePrivateEndpoints && openAIAccountId != '') {
  name: '${baseName}-${environmentName}-openai-pe'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[1].id
    }
    privateLinkServiceConnections: [
      {
        name: '${baseName}-${environmentName}-openai-psc'
        properties: {
          privateLinkServiceId: openAIAccountId
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

resource openAIPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-04-01' = if (enablePrivateEndpoints && openAIAccountId != '') {
  parent: openAIPrivateEndpoint
  name: 'openai-dns-group'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'openai-config'
        properties: {
          privateDnsZoneId: openAIDnsZone.id
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output containerAppsSubnetId string = vnet.properties.subnets[0].id
output privateEndpointSubnetId string = vnet.properties.subnets[1].id
output cosmosDnsZoneId string = cosmosDnsZone.id
output openAIDnsZoneId string = openAIDnsZone.id
