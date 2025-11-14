using '../main.bicep'

// Staging Environment Parameters
param location = 'eastus2'
param environmentName = 'staging'
param baseName = 'openai-workshop'

param tags = {
  Environment: 'Staging'
  Application: 'OpenAI-Workshop'
  ManagedBy: 'Bicep'
  CostCenter: 'Engineering'
  Owner: 'DevTeam'
}
