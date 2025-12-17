@description('Principal ID to grant Cosmos DB data plane roles to')
param principalId string

@description('Name of the Cosmos DB account')
param cosmosDbAccountName string

@description('Optional role assignment name suffix to keep GUIDs unique per principal type')
param roleAssignmentSalt string = ''

var cosmosDbDataOwnerRoleId = '00000000-0000-0000-0000-000000000001'
var cosmosDbDataContributorRoleId = '00000000-0000-0000-0000-000000000002'
var salt = empty(roleAssignmentSalt) ? principalId : '${principalId}-${roleAssignmentSalt}'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: cosmosDbAccountName
}

resource cosmosDataOwner 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  name: guid(cosmosDbDataOwnerRoleId, salt, cosmosAccount.id)
  parent: cosmosAccount
  properties: {
    principalId: principalId
    roleDefinitionId: resourceId('Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions', cosmosAccount.name, cosmosDbDataOwnerRoleId)
    scope: cosmosAccount.id
  }
}

resource cosmosDataContributor 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-05-15' = {
  name: guid(cosmosDbDataContributorRoleId, salt, cosmosAccount.id)
  parent: cosmosAccount
  properties: {
    principalId: principalId
    roleDefinitionId: resourceId('Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions', cosmosAccount.name, cosmosDbDataContributorRoleId)
    scope: cosmosAccount.id
  }
}

output dataOwnerRoleAssignmentId string = cosmosDataOwner.id
output dataContributorRoleAssignmentId string = cosmosDataContributor.id
