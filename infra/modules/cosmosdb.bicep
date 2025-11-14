// Cosmos DB deployment with containers for MCP data
param location string
param baseName string
param environmentName string
param tags object

var cosmosDbName = '${baseName}-${environmentName}-cosmos'
var databaseName = 'contoso'

resource cosmosDb 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: cosmosDbName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: false
    locations: [
      {
        failoverPriority: 0
        isZoneRedundant: false
        locationName: location
      }
    ]
    capabilities: [
      {
        name: 'EnableNoSQLVectorSearch'
      }
    ]
  }
  tags: tags
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosDb
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// Customers container
resource customersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Customers'
  properties: {
    resource: {
      id: 'Customers'
      partitionKey: {
        paths: ['/customer_id']
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
      }
    }
  }
}

// Subscriptions container
resource subscriptionsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Subscriptions'
  properties: {
    resource: {
      id: 'Subscriptions'
      partitionKey: {
        paths: ['/customer_id']
        kind: 'Hash'
      }
    }
  }
}

// Products container
resource productsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Products'
  properties: {
    resource: {
      id: 'Products'
      partitionKey: {
        paths: ['/category']
        kind: 'Hash'
      }
    }
  }
}

// Promotions container
resource promotionsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Promotions'
  properties: {
    resource: {
      id: 'Promotions'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
      }
    }
  }
}

// Agent State Store container
resource agentStateContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'workshop_agent_state_store'
  properties: {
    resource: {
      id: 'workshop_agent_state_store'
      partitionKey: {
        paths: ['/session_id']
        kind: 'Hash'
      }
    }
  }
}

output endpoint string = cosmosDb.properties.documentEndpoint
output primaryKey string = cosmosDb.listKeys().primaryMasterKey
output databaseName string = databaseName
output accountName string = cosmosDb.name
