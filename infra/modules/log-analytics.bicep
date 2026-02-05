// Log Analytics Workspace for Container Apps
param location string
param baseName string
param environmentName string
param tags object

@description('Log Analytics SKU')
param sku string = 'PerGB2018'

@description('Log retention in days')
param retentionInDays int = 30

var workspaceName = '${baseName}-${environmentName}-logs'

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: workspaceName
  location: location
  properties: {
    sku: {
      name: sku
    }
    retentionInDays: retentionInDays
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    workspaceCapping: {
      dailyQuotaGb: 1
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  tags: tags
}

// Application Insights for observability
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${baseName}-${environmentName}-appinsights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
  tags: tags
}

output workspaceId string = logAnalytics.id
output customerId string = logAnalytics.properties.customerId
output workspaceName string = logAnalytics.name
output applicationInsightsConnectionString string = applicationInsights.properties.ConnectionString
output applicationInsightsInstrumentationKey string = applicationInsights.properties.InstrumentationKey
