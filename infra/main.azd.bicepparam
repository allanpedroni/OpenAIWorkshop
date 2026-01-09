using './main.azd.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'openaiworkshop')
param location = readEnvironmentVariable('AZURE_LOCATION', 'westus')
param mcpImageName = readEnvironmentVariable('CUSTOM_MCP_IMAGE_NAME', 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest')
param appImageName = readEnvironmentVariable('CUSTOM_APP_IMAGE_NAME', 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest')
param aadTenantId = readEnvironmentVariable('AAD_TENANT_ID', '')
param aadFrontendClientId = readEnvironmentVariable('AAD_FRONTEND_CLIENT_ID', '')
param aadApiAudience = readEnvironmentVariable('AAD_API_AUDIENCE', '')
param allowedEmailDomain = readEnvironmentVariable('AAD_ALLOWED_DOMAIN', 'microsoft.com')
param disableAuthSetting = readEnvironmentVariable('DISABLE_AUTH', 'false')
param secureCosmosConnectivity = toLower(readEnvironmentVariable('SECURE_COSMOS_CONNECTIVITY', 'true')) == 'true'
param vnetAddressPrefix = readEnvironmentVariable('SECURE_VNET_ADDRESS_PREFIX', '10.90.0.0/16')
param containerAppsSubnetPrefix = readEnvironmentVariable('SECURE_CONTAINERAPPS_SUBNET_PREFIX', '10.90.0.0/23')
param privateEndpointSubnetPrefix = readEnvironmentVariable('SECURE_PRIVATE_ENDPOINT_SUBNET_PREFIX', '10.90.2.0/24')
param localDeveloperObjectId = readEnvironmentVariable('LOCAL_DEVELOPER_OBJECT_ID', '')
