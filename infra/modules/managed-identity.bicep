@description('Azure region where the managed identity will be created')
param location string

@description('Base name for the managed identity resource')
param name string

@description('Resource tags applied to the managed identity')
param tags object

resource userIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

output resourceId string = userIdentity.id
output clientId string = userIdentity.properties.clientId
output principalId string = userIdentity.properties.principalId
