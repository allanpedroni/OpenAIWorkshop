using '../main.bicep'

// Production Environment Parameters
param location = 'eastus2'
param environmentName = 'prod'
param baseName = 'openai-workshop'

param tags = {
  Environment: 'Production'
  Application: 'OpenAI-Workshop'
  ManagedBy: 'Bicep'
  CostCenter: 'Production'
  Owner: 'DevOps'
  Criticality: 'High'
}
