# Azure Deployment Guide

This guide walks through deploying the OpenAI Workshop application to Azure using Bicep Infrastructure as Code.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Detailed Steps](#detailed-steps)
5. [Post-Deployment Configuration](#post-deployment-configuration)
6. [Monitoring and Troubleshooting](#monitoring-and-troubleshooting)
7. [CI/CD Pipeline Setup](#cicd-pipeline-setup)

## Architecture Overview

### Azure Services

```
┌─────────────────────────────────────────────────────────────┐
│                      Azure Subscription                      │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │            Resource Group (openai-workshop-dev-rg)      │ │
│  │                                                          │ │
│  │  ┌──────────────┐    ┌────────────────┐                │ │
│  │  │ Azure OpenAI │    │   Cosmos DB    │                │ │
│  │  │              │    │                │                │ │
│  │  │ - GPT-5-Chat │    │ - Customers    │                │ │
│  │  │ - Embeddings │    │ - Products     │                │ │
│  │  └──────────────┘    │ - Agent State  │                │ │
│  │                      └────────────────┘                 │ │
│  │                                                          │ │
│  │  ┌────────────────────────────────────────────────────┐ │ │
│  │  │       Container Apps Environment                   │ │ │
│  │  │  ┌───────────────┐    ┌────────────────────────┐  │ │ │
│  │  │  │  MCP Service  │    │    Application         │  │ │ │
│  │  │  │               │◄───┤                        │  │ │ │
│  │  │  │  Port: 8000   │    │  Backend: FastAPI      │  │ │ │
│  │  │  │  Auto-scale   │    │  Frontend: React       │  │ │ │
│  │  │  │  1-3 replicas │    │  Port: 3000            │  │ │ │
│  │  │  └───────────────┘    │  Auto-scale: 1-5       │  │ │ │
│  │  │                       └────────────────────────┘  │ │ │
│  │  └────────────────────────────────────────────────────┘ │ │
│  │                                                          │ │
│  │  ┌─────────────────┐    ┌──────────────────────────┐  │ │
│  │  │  Container      │    │  Log Analytics           │  │ │
│  │  │  Registry (ACR) │    │  Workspace               │  │ │
│  │  │                 │    │                          │  │ │
│  │  │  - mcp-service  │    │  - Container logs        │  │ │
│  │  │  - workshop-app │    │  - Metrics & monitoring  │  │ │
│  │  └─────────────────┘    └──────────────────────────┘  │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Traffic Flow

1. User → **Application Container** (Port 3000)
2. Application → **MCP Service** (internal communication)
3. Application → **Azure OpenAI** (GPT-5-Chat API)
4. Application → **Cosmos DB** (state persistence)
5. MCP Service → **Cosmos DB** (customer data access)

## Prerequisites

### Required Tools

| Tool | Version | Installation |
|------|---------|--------------|
| Azure CLI | 2.50+ | https://aka.ms/azure-cli |
| Docker Desktop | 24.0+ | https://www.docker.com/products/docker-desktop |
| PowerShell | 7.0+ | https://github.com/PowerShell/PowerShell |
| Git | Latest | https://git-scm.com/downloads |

### Azure Requirements

- **Subscription**: Active Azure subscription with Owner or Contributor role
- **Quotas**: Ensure sufficient quotas for:
  - Azure OpenAI (GPT-5-Chat deployment)
  - Container Apps (minimum 2 apps)
  - Cosmos DB (1 account)
- **Resource Providers**: Register these providers:
  ```powershell
  az provider register --namespace Microsoft.App
  az provider register --namespace Microsoft.CognitiveServices
  az provider register --namespace Microsoft.DocumentDB
  az provider register --namespace Microsoft.ContainerRegistry
  az provider register --namespace Microsoft.OperationalInsights
  ```

## Quick Start

### 1. Clone Repository

```powershell
git clone https://github.com/your-org/OpenAIWorkshop.git
cd OpenAIWorkshop
```

### 2. Login to Azure

```powershell
az login
az account set --subscription "<your-subscription-id>"
```

### 3. Deploy to Dev Environment

**Option A: Using Azure Developer CLI (azd) - Recommended**

```bash
# Install azd if not already installed
# Windows: powershell -ex AllSigned -c "Invoke-RestMethod 'https://aka.ms/install-azd.ps1' | Invoke-Expression"
# macOS/Linux: curl -fsSL https://aka.ms/install-azd.sh | bash

# Login and deploy everything with one command
azd auth login
azd up
```

See [AZD_DEPLOYMENT.md](./AZD_DEPLOYMENT.md) for complete azd documentation.

**Option B: Using PowerShell Script**

```powershell
cd infra
./deploy.ps1 -Environment dev
```

Both options will:
- ✅ Create all Azure resources
- ✅ Build Docker images
- ✅ Push images to ACR
- ✅ Deploy containers
- ✅ Output application URL

### 4. Access Application

After deployment completes, open the Application URL provided in the output:

```
https://openai-workshop-dev-app.<region>.azurecontainerapps.io
```

## Detailed Steps

### Step 1: Configure Parameters

Edit environment parameter files as needed:

```powershell
# Edit dev parameters
code infra/parameters/dev.bicepparam
```

Example customizations:

```bicep
using '../main.bicep'

param location = 'westus2'  // Change region
param baseName = 'my-company-workshop'  // Custom naming
param environmentName = 'dev'

param tags = {
  Environment: 'Development'
  CostCenter: 'AI-Research'
  Owner: 'john.doe@company.com'
}
```

### Step 2: Validate Bicep Templates

Before deployment, validate templates:

```powershell
cd infra

# Validate with parameter file
az deployment sub validate `
  --location eastus2 `
  --template-file main.bicep `
  --parameters parameters/dev.bicepparam
```

### Step 3: Deploy Infrastructure

Choose your deployment method:

#### Option A: Azure Developer CLI (azd) - Simplest

```bash
# Full deployment with one command
azd up

# Or separate steps
azd provision  # Infrastructure only
azd deploy     # Code deployment only

# Deploy specific service
azd deploy mcp
azd deploy app
```

**Benefits:**
- Single command deployment
- Built-in environment management
- Automatic state tracking
- Easy CI/CD integration

See [AZD_DEPLOYMENT.md](./AZD_DEPLOYMENT.md) for complete azd documentation.

#### Option B: PowerShell Script

```powershell
# Full deployment (infra + containers)
./deploy.ps1 -Environment dev

# Infrastructure only
./deploy.ps1 -Environment dev -InfraOnly

# Skip builds (use existing images)
./deploy.ps1 -Environment dev -SkipBuild

# Custom parameters
./deploy.ps1 -Environment staging -Location westus2 -BaseName my-workshop
```

#### Option C: Manual Bicep Deployment

```powershell
# With parameter file
az deployment sub create `
  --location eastus2 `
  --template-file main.bicep `
  --parameters parameters/dev.bicepparam `
  --name "workshop-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"

# With inline parameters
az deployment sub create `
  --location eastus2 `
  --template-file main.bicep `
  --parameters location=eastus2 environmentName=dev baseName=workshop `
  --name "workshop-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

### Step 4: Build and Push Docker Images

**Note:** Skip this step if using `azd up` or `./deploy.ps1` - they handle this automatically.

If deploying manually:

#### MCP Service:

```powershell
cd mcp

# Build image
docker build -t openaiworkshopdevacr.azurecr.io/mcp-service:latest -f Dockerfile .

# Login to ACR
az acr login --name openaiworkshopdevacr

# Push image
docker push openaiworkshopdevacr.azurecr.io/mcp-service:latest
```

#### Application:

```powershell
cd agentic_ai/applications

# Build image (multi-stage: React + Python)
docker build -t openaiworkshopdevacr.azurecr.io/workshop-app:latest -f Dockerfile .

# Push image
docker push openaiworkshopdevacr.azurecr.io/workshop-app:latest
```

### Step 5: Verify Deployment

Check Container App status:

```powershell
# List container apps
az containerapp list `
  --resource-group openai-workshop-dev-rg `
  --output table

# Check application status
az containerapp show `
  --name openai-workshop-dev-app `
  --resource-group openai-workshop-dev-rg `
  --query "properties.runningStatus"

# Check MCP service status
az containerapp show `
  --name openai-workshop-dev-mcp `
  --resource-group openai-workshop-dev-rg `
  --query "properties.runningStatus"
```

## Post-Deployment Configuration

### 1. Enable Authentication (Optional)

Edit Container App environment variables:

```powershell
az containerapp update `
  --name openai-workshop-dev-app `
  --resource-group openai-workshop-dev-rg `
  --set-env-vars DISABLE_AUTH=false AAD_TENANT_ID=<tenant-id>
```

### 2. Configure Custom Domain

```powershell
# Add custom domain
az containerapp hostname add `
  --hostname www.myapp.com `
  --resource-group openai-workshop-dev-rg `
  --name openai-workshop-dev-app

# Bind certificate
az containerapp hostname bind `
  --hostname www.myapp.com `
  --resource-group openai-workshop-dev-rg `
  --name openai-workshop-dev-app `
  --certificate <certificate-id>
```

### 3. Scale Configuration

Modify scaling rules:

```powershell
az containerapp update `
  --name openai-workshop-dev-app `
  --resource-group openai-workshop-dev-rg `
  --min-replicas 2 `
  --max-replicas 10
```

### 4. Seed Cosmos DB Data

If needed, seed database with sample data:

```powershell
# Run a script or use Azure Portal Data Explorer
# Sample customers, products, promotions
```

## Monitoring and Troubleshooting

### View Logs

#### Real-time logs:

```powershell
# Application logs
az containerapp logs show `
  --name openai-workshop-dev-app `
  --resource-group openai-workshop-dev-rg `
  --follow

# MCP service logs
az containerapp logs show `
  --name openai-workshop-dev-mcp `
  --resource-group openai-workshop-dev-rg `
  --follow
```

#### Log Analytics queries:

```powershell
# Open Log Analytics workspace
az monitor log-analytics workspace show `
  --resource-group openai-workshop-dev-rg `
  --workspace-name openai-workshop-dev-logs
```

Example KQL queries:

```kql
// Recent errors
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "openai-workshop-dev-app"
| where Log_s contains "error" or Log_s contains "exception"
| order by TimeGenerated desc
| take 100

// Request rates
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| summarize RequestCount = count() by bin(TimeGenerated, 5m), ContainerAppName_s
| render timechart
```

### Common Issues

#### Issue 1: Container fails to start

**Symptoms**: Container status shows "Failed" or "CrashLoopBackOff"

**Diagnosis**:
```powershell
az containerapp logs show --name <app-name> --resource-group <rg-name>
```

**Solutions**:
- Check environment variables are set correctly
- Verify image exists in ACR
- Check Cosmos DB connection string
- Review application startup logs

#### Issue 2: Cannot access application URL

**Symptoms**: 502 Bad Gateway or timeout

**Diagnosis**:
```powershell
az containerapp show --name <app-name> --resource-group <rg-name> --query "properties.configuration.ingress"
```

**Solutions**:
- Verify ingress is enabled and external
- Check container is listening on correct port
- Review NSG rules (if custom networking)

#### Issue 3: OpenAI quota exceeded

**Symptoms**: 429 errors in logs

**Solutions**:
- Check quota in Azure Portal: Azure OpenAI > Quotas
- Request quota increase
- Implement retry logic with exponential backoff

#### Issue 4: High latency

**Diagnosis**:
```powershell
# Check current replicas
az containerapp replica list `
  --name <app-name> `
  --resource-group <rg-name>
```

**Solutions**:
- Increase min replicas
- Adjust scaling threshold
- Check OpenAI API latency
- Review Cosmos DB RU consumption

### Performance Monitoring

#### Application Insights (optional):

```powershell
# Enable Application Insights
az monitor app-insights component create `
  --app workshop-insights `
  --location eastus2 `
  --resource-group openai-workshop-dev-rg `
  --workspace <log-analytics-workspace-id>

# Link to Container App
az containerapp update `
  --name openai-workshop-dev-app `
  --resource-group openai-workshop-dev-rg `
  --set-env-vars APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
```

## CI/CD Pipeline Setup

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main, develop]
  workflow_dispatch:

env:
  AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

jobs:
  deploy-dev:
    if: github.ref == 'refs/heads/develop'
    runs-on: windows-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy Infrastructure and Containers
        shell: pwsh
        run: |
          cd infra
          ./deploy.ps1 -Environment dev
  
  deploy-prod:
    if: github.ref == 'refs/heads/main'
    runs-on: windows-latest
    environment: production
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy Infrastructure and Containers
        shell: pwsh
        run: |
          cd infra
          ./deploy.ps1 -Environment prod
```

### Azure DevOps Pipeline

Create `azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'windows-latest'

variables:
  azureSubscription: 'Azure-ServiceConnection'

stages:
  - stage: Deploy_Dev
    condition: eq(variables['Build.SourceBranch'], 'refs/heads/develop')
    jobs:
      - job: DeployInfrastructure
        steps:
          - task: AzureCLI@2
            displayName: 'Deploy to Dev'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'pscore'
              scriptLocation: 'scriptPath'
              scriptPath: 'infra/deploy.ps1'
              arguments: '-Environment dev'

  - stage: Deploy_Prod
    condition: eq(variables['Build.SourceBranch'], 'refs/heads/main')
    jobs:
      - deployment: DeployInfrastructure
        environment: 'production'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  displayName: 'Deploy to Production'
                  inputs:
                    azureSubscription: $(azureSubscription)
                    scriptType: 'pscore'
                    scriptLocation: 'scriptPath'
                    scriptPath: 'infra/deploy.ps1'
                    arguments: '-Environment prod'
```

## Cleanup

### Delete Resources

```powershell
# Delete resource group and all resources
az group delete --name openai-workshop-dev-rg --yes --no-wait

# Or delete specific resources
az containerapp delete --name openai-workshop-dev-app --resource-group openai-workshop-dev-rg
az containerapp delete --name openai-workshop-dev-mcp --resource-group openai-workshop-dev-rg
```

## Cost Management

### Estimated Monthly Costs (Dev Environment)

| Service | SKU/Config | Estimated Cost |
|---------|------------|----------------|
| Azure OpenAI | GPT-5-Chat + Embeddings | $100-500/month* |
| Cosmos DB | 400 RU/s | $24/month |
| Container Apps | 2 apps, 1-3 replicas | $30-100/month |
| Container Registry | Basic | $5/month |
| Log Analytics | 5GB/month | Free tier |
| **Total** | | **$159-629/month** |

*Depends on usage volume

### Cost Optimization Tips

1. **Use Dev SKUs**: Smaller SKUs for non-production environments
2. **Auto-shutdown**: Delete dev resources outside business hours
3. **Reserved Capacity**: Purchase reserved instances for production
4. **Monitoring**: Set up cost alerts in Azure Cost Management

## Additional Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure OpenAI Service Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Bicep Language Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure Cosmos DB Documentation](https://learn.microsoft.com/azure/cosmos-db/)
- [Project README](../README.md)

## Support

For issues:
1. Check logs with `az containerapp logs`
2. Review Azure Portal for resource health
3. Consult the troubleshooting section above
4. Open an issue in the GitHub repository
