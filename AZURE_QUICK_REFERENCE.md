# Azure Deployment Quick Reference

Quick reference for common Azure deployment commands for the OpenAI Workshop.

## Quick Start

### Option 1: Azure Developer CLI (azd) - Simplest

```bash
# Login and deploy everything with one command
azd auth login
azd up

# Access your application
# URL will be displayed at the end of deployment
```

### Option 2: PowerShell Script

```powershell
# Login and set subscription
az login
az account set --subscription <subscription-id>

# Deploy everything (dev environment)
cd infra
./deploy.ps1 -Environment dev

# Access your application
# URL will be displayed at the end of deployment
```

## Azure Developer CLI (azd) Commands

### Deployment
```bash
# Full deployment (infrastructure + code)
azd up

# Provision infrastructure only
azd provision

# Deploy code only
azd deploy

# Deploy specific service
azd deploy mcp
azd deploy app
```

### Environment Management
```bash
# Create new environment
azd env new dev
azd env new staging
azd env new prod

# Select environment
azd env select dev

# List environments
azd env list

# Set environment variables
azd env set AZURE_LOCATION eastus2
azd env set DISABLE_AUTH true

# View all environment values
azd env get-values
```

### Monitoring
```bash
# View logs (follow mode)
azd monitor --logs

# View logs for specific service
azd monitor --logs --service app
azd monitor --logs --service mcp

# Open Azure Portal
azd monitor --portal
```

### Cleanup
```bash
# Delete all resources
azd down

# Delete resources and environment
azd down --purge
```

## PowerShell Script Commands

### Full Deployment
```powershell
# Deploy infrastructure + build images + push to ACR
./deploy.ps1 -Environment dev

# Deploy to staging
./deploy.ps1 -Environment staging

# Deploy to production
./deploy.ps1 -Environment prod
```

### Infrastructure Only
```powershell
# Deploy Azure resources without building containers
./deploy.ps1 -Environment dev -InfraOnly
```

### Skip Build
```powershell
# Deploy with existing images (faster for config changes)
./deploy.ps1 -Environment dev -SkipBuild
```

### Custom Parameters
```powershell
# Deploy with custom location and base name
./deploy.ps1 -Environment dev -Location westus2 -BaseName my-workshop
```

## Manual Bicep Deployment

```powershell
# Deploy with parameter file
az deployment sub create \
  --location eastus2 \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam \
  --name "workshop-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

# Deploy with inline parameters
az deployment sub create \
  --location eastus2 \
  --template-file main.bicep \
  --parameters location=eastus2 environmentName=dev baseName=workshop
```

## Docker Commands

### Build Images
```powershell
# MCP Service
cd mcp
docker build -t <acr-name>.azurecr.io/mcp-service:latest .

# Application
cd agentic_ai/applications
docker build -t <acr-name>.azurecr.io/workshop-app:latest .
```

### Push Images
```powershell
# Login to ACR
az acr login --name <acr-name>

# Push MCP Service
docker push <acr-name>.azurecr.io/mcp-service:latest

# Push Application
docker push <acr-name>.azurecr.io/workshop-app:latest
```

## Container App Management

### View Status
```powershell
# List all container apps
az containerapp list --resource-group openai-workshop-dev-rg --output table

# Show specific app status
az containerapp show \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --query "properties.runningStatus"
```

### View Logs
```powershell
# Real-time logs (follow)
az containerapp logs show \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --follow

# Last 50 lines
az containerapp logs show \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --tail 50

# MCP service logs
az containerapp logs show \
  --name openai-workshop-dev-mcp \
  --resource-group openai-workshop-dev-rg \
  --follow
```

### Restart Containers
```powershell
# Restart application
az containerapp revision restart \
  --resource-group openai-workshop-dev-rg \
  --name openai-workshop-dev-app \
  --revision latest

# Restart MCP service
az containerapp revision restart \
  --resource-group openai-workshop-dev-rg \
  --name openai-workshop-dev-mcp \
  --revision latest
```

### Scale Containers
```powershell
# Update scaling rules
az containerapp update \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --min-replicas 2 \
  --max-replicas 10

# Check current replicas
az containerapp replica list \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg
```

### Update Environment Variables
```powershell
# Set environment variable
az containerapp update \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --set-env-vars DISABLE_AUTH=false

# Add multiple environment variables
az containerapp update \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --set-env-vars VAR1=value1 VAR2=value2
```

## Resource Management

### List Resources
```powershell
# All resources in resource group
az resource list --resource-group openai-workshop-dev-rg --output table

# Specific resource types
az resource list --resource-group openai-workshop-dev-rg --resource-type Microsoft.App/containerApps
```

### Get Resource Details
```powershell
# Azure OpenAI
az cognitiveservices account show \
  --name openai-workshop-dev-openai \
  --resource-group openai-workshop-dev-rg

# Cosmos DB
az cosmosdb show \
  --name openai-workshop-dev-cosmos \
  --resource-group openai-workshop-dev-rg

# Container Registry
az acr show \
  --name <acr-name> \
  --resource-group openai-workshop-dev-rg
```

### Delete Resources
```powershell
# Delete entire resource group (CAUTION!)
az group delete --name openai-workshop-dev-rg --yes --no-wait

# Delete specific container app
az containerapp delete \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg
```

## Monitoring

### View Application URL
```powershell
# Get application FQDN
az containerapp show \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv

# Open in browser (Windows)
start "https://$(az containerapp show --name openai-workshop-dev-app --resource-group openai-workshop-dev-rg --query 'properties.configuration.ingress.fqdn' -o tsv)"
```

### Log Analytics
```powershell
# Get workspace ID
az monitor log-analytics workspace show \
  --resource-group openai-workshop-dev-rg \
  --workspace-name openai-workshop-dev-logs \
  --query "customerId" -o tsv

# Query logs (example KQL)
az monitor log-analytics query \
  --workspace <workspace-id> \
  --analytics-query "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(1h) | take 100"
```

### View Metrics
```powershell
# CPU usage
az monitor metrics list \
  --resource /subscriptions/<sub-id>/resourceGroups/openai-workshop-dev-rg/providers/Microsoft.App/containerApps/openai-workshop-dev-app \
  --metric "CpuUsage" \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z

# Memory usage
az monitor metrics list \
  --resource /subscriptions/<sub-id>/resourceGroups/openai-workshop-dev-rg/providers/Microsoft.App/containerApps/openai-workshop-dev-app \
  --metric "MemoryUsage"
```

## Cosmos DB Operations

### List Containers
```powershell
# List databases
az cosmosdb sql database list \
  --account-name openai-workshop-dev-cosmos \
  --resource-group openai-workshop-dev-rg

# List containers in database
az cosmosdb sql container list \
  --account-name openai-workshop-dev-cosmos \
  --resource-group openai-workshop-dev-rg \
  --database-name workshop_db
```

### Get Connection String
```powershell
# Get primary connection string
az cosmosdb keys list \
  --name openai-workshop-dev-cosmos \
  --resource-group openai-workshop-dev-rg \
  --type connection-strings \
  --query "connectionStrings[0].connectionString" -o tsv
```

## Azure OpenAI Operations

### List Models
```powershell
# List deployments
az cognitiveservices account deployment list \
  --name openai-workshop-dev-openai \
  --resource-group openai-workshop-dev-rg

# Get specific deployment
az cognitiveservices account deployment show \
  --name openai-workshop-dev-openai \
  --resource-group openai-workshop-dev-rg \
  --deployment-name gpt-4
```

### Get Keys
```powershell
# List keys
az cognitiveservices account keys list \
  --name openai-workshop-dev-openai \
  --resource-group openai-workshop-dev-rg
```

## Troubleshooting

### Validate Bicep
```powershell
# Validate template
az deployment sub validate \
  --location eastus2 \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam

# What-if analysis
az deployment sub what-if \
  --location eastus2 \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam
```

### Check Deployment Status
```powershell
# List deployments
az deployment sub list --query "[?name contains 'workshop'].{Name:name, State:properties.provisioningState, Timestamp:properties.timestamp}" --output table

# Show deployment details
az deployment sub show --name <deployment-name>

# Show deployment operations
az deployment operation sub list --name <deployment-name>
```

### Diagnose Container Issues
```powershell
# Get revision details
az containerapp revision show \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --revision latest

# List revisions
az containerapp revision list \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg

# Execute command in container
az containerapp exec \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --command "/bin/bash"
```

### Check Activity Log
```powershell
# Recent activity
az monitor activity-log list \
  --resource-group openai-workshop-dev-rg \
  --start-time 2024-01-01T00:00:00Z \
  --offset 1d

# Errors only
az monitor activity-log list \
  --resource-group openai-workshop-dev-rg \
  --query "[?level=='Error']"
```

## Cost Management

### View Costs
```powershell
# View current costs (requires Cost Management API)
az consumption usage list \
  --start-date 2024-01-01 \
  --end-date 2024-01-31 \
  --query "[?contains(instanceName, 'workshop')]"

# Set budget alert (in Azure Portal)
# Cost Management + Billing > Budgets > Add
```

## Backup and Export

### Export Template
```powershell
# Export resource group as template
az group export \
  --name openai-workshop-dev-rg \
  --output-file exported-template.json
```

### Backup Cosmos DB
```powershell
# Enable continuous backup (requires recreation)
az cosmosdb update \
  --name openai-workshop-dev-cosmos \
  --resource-group openai-workshop-dev-rg \
  --backup-policy-type Continuous
```

## Common Resource Names

### Development Environment
- **Resource Group**: `openai-workshop-dev-rg`
- **Azure OpenAI**: `openai-workshop-dev-openai`
- **Cosmos DB**: `openai-workshop-dev-cosmos`
- **Container Registry**: `openaiworkshopdevacr` (no hyphens)
- **Log Analytics**: `openai-workshop-dev-logs`
- **Container Apps Environment**: `openai-workshop-dev-env`
- **MCP Service**: `openai-workshop-dev-mcp`
- **Application**: `openai-workshop-dev-app`

### Staging Environment
Replace `dev` with `staging` in all names above.

### Production Environment
Replace `dev` with `prod` in all names above.

## Environment Variables Reference

### Backend Application
```
AZURE_OPENAI_ENDPOINT=<openai-endpoint>
AZURE_OPENAI_API_KEY=<openai-key>
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2025-03-01-preview
OPENAI_MODEL_NAME=gpt-4
MCP_SERVER_URI=<mcp-service-url>
COSMOSDB_ENDPOINT=<cosmos-endpoint>
COSMOSDB_KEY=<cosmos-key>
COSMOS_DB_NAME=workshop_db
COSMOS_CONTAINER_NAME=workshop_agent_state_store
DISABLE_AUTH=true
AGENT_MODULE=agents.agent_framework.single_agent
```

### MCP Service
```
COSMOSDB_ENDPOINT=<cosmos-endpoint>
COSMOSDB_KEY=<cosmos-key>
COSMOS_DB_NAME=workshop_db
```

## Quick Tests

### Test Application
```powershell
# Get agents list
$APP_URL = az containerapp show --name openai-workshop-dev-app --resource-group openai-workshop-dev-rg --query "properties.configuration.ingress.fqdn" -o tsv
curl "https://$APP_URL/agents"

# Test health
curl "https://$APP_URL/"
```

### Test from Browser
1. Open application URL
2. F12 for DevTools
3. Console tab - check for errors
4. Network tab - check API calls
5. WebSocket tab - verify streaming connection

## Useful Links

- **Azure Portal**: https://portal.azure.com
- **Log Analytics Workspace**: Navigate to resource in portal
- **Container Apps**: Navigate to resource in portal
- **Cosmos DB Data Explorer**: Navigate to resource > Data Explorer
- **Cost Management**: Portal > Cost Management + Billing

---

**Pro Tips:**

1. Use `--output table` for readable output
2. Use `--query` with JMESPath for filtering
3. Use `-o tsv` for script-friendly output
4. Save commonly used commands as scripts
5. Use `az find` to discover commands
6. Use `--help` for detailed command info

**Example workflow:**
```powershell
# Check status
az containerapp list -g openai-workshop-dev-rg -o table

# View logs if issue found
az containerapp logs show --name openai-workshop-dev-app -g openai-workshop-dev-rg --tail 100

# Restart if needed
az containerapp revision restart --name openai-workshop-dev-app -g openai-workshop-dev-rg --revision latest

# Verify fix
curl https://$(az containerapp show --name openai-workshop-dev-app -g openai-workshop-dev-rg --query 'properties.configuration.ingress.fqdn' -o tsv)/agents
```
