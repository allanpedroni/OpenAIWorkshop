// Fraud Detection Durable Workflow Container App
// Includes DTS Emulator + Worker + Backend in one container

@description('Azure region for deployment')
param location string

@description('Base name for resources')
param baseName string

@description('Container Apps Environment resource ID')
param containerAppsEnvironmentId string

@description('Container Registry name')
param containerRegistryName string

@description('Azure OpenAI endpoint URL')
param azureOpenAIEndpoint string

@description('Azure OpenAI API key')
@secure()
param azureOpenAIKey string

@description('Azure OpenAI deployment name')
param azureOpenAIDeploymentName string

@description('MCP service URL (internal)')
param mcpServiceUrl string

@description('Optional user-assigned managed identity resource ID')
param userAssignedIdentityResourceId string = ''

@description('Client ID for the user-assigned managed identity')
param userAssignedIdentityClientId string = ''

@description('Application Insights connection string for observability')
param applicationInsightsConnectionString string = ''

@description('Resource tags')
param tags object

@description('Container image tag')
param imageTag string = 'latest'

@description('Full container image name from azd')
param imageName string = ''

var appName = '${baseName}-fraud-wf'
var containerImage = !empty(imageName) ? imageName : '${containerRegistryName}.azurecr.io/fraud-workflow:${imageTag}'
var azdTags = union(tags, {
  'azd-service-name': 'fraud-workflow'
  'azd-service-type': 'containerapp'
})

var managedIdentityEnv = !empty(userAssignedIdentityClientId) ? [
  {
    name: 'AZURE_CLIENT_ID'
    value: userAssignedIdentityClientId
  }
] : []

var observabilityEnv = !empty(applicationInsightsConnectionString) ? [
  {
    name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
    value: applicationInsightsConnectionString
  }
] : []

resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' existing = {
  name: containerRegistryName
}

resource fraudWorkflow 'Microsoft.App/containerApps@2023-05-01' = {
  name: appName
  location: location
  identity: empty(userAssignedIdentityResourceId) ? null : {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      ingress: {
        external: true
        targetPort: 8002
        transport: 'http'
        allowInsecure: false
        corsPolicy: {
          allowedOrigins: ['*']
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
          allowedHeaders: ['*']
          allowCredentials: true
        }
      }
      registries: [
        {
          server: '${containerRegistryName}.azurecr.io'
          identity: !empty(userAssignedIdentityResourceId) ? userAssignedIdentityResourceId : 'system'
        }
      ]
      secrets: [
        {
          name: 'azure-openai-key'
          value: azureOpenAIKey
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'fraud-workflow'
          image: containerImage
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: concat([
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: azureOpenAIEndpoint
            }
            {
              name: 'AZURE_OPENAI_API_KEY'
              secretRef: 'azure-openai-key'
            }
            {
              name: 'AZURE_OPENAI_CHAT_DEPLOYMENT'
              value: azureOpenAIDeploymentName
            }
            {
              name: 'MCP_SERVER_URI'
              value: mcpServiceUrl
            }
            {
              name: 'DTS_ENDPOINT'
              value: 'http://localhost:8080'
            }
            {
              name: 'DTS_TASKHUB'
              value: 'default'
            }
            {
              name: 'BACKEND_PORT'
              value: '8002'
            }
          ], managedIdentityEnv, observabilityEnv)
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8002
              }
              initialDelaySeconds: 60
              periodSeconds: 30
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health'
                port: 8002
              }
              initialDelaySeconds: 30
              periodSeconds: 10
            }
          ]
        }
        // DTS Emulator sidecar container
        {
          name: 'dts-emulator'
          image: 'mcr.microsoft.com/dts/dts-emulator:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'DTS_PORT'
              value: '8080'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scaling'
            http: {
              metadata: {
                concurrentRequests: '50'
              }
            }
          }
        ]
      }
    }
  }
  tags: azdTags
}

@description('Fraud workflow FQDN')
output fqdn string = fraudWorkflow.properties.configuration.ingress.fqdn

@description('Fraud workflow URL')
output url string = 'https://${fraudWorkflow.properties.configuration.ingress.fqdn}'

@description('Fraud workflow resource name')
output name string = fraudWorkflow.name
