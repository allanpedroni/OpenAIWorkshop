using './main.azd.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'openaiworkshop')
param location = readEnvironmentVariable('AZURE_LOCATION', 'westus')
param mcpImageName = readEnvironmentVariable('SERVICE_MCP_IMAGE_NAME', '')
param appImageName = readEnvironmentVariable('SERVICE_APP_IMAGE_NAME', '')
