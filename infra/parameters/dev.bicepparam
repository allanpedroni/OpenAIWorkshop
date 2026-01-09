using '../main.bicep'

// Development Environment Parameters
param location = 'eastus2'
param environmentName = 'dev'
param baseName = 'openai-workshop'

param tags = {
  Environment: 'Development'
  Application: 'OpenAI-Workshop'
  ManagedBy: 'Bicep'
  CostCenter: 'Engineering'
  Owner: 'DevTeam'
}
