# Azure Developer CLI (azd) Deployment Guide

This guide explains how to deploy the OpenAI Workshop using Azure Developer CLI (azd).

## Prerequisites

### Install Azure Developer CLI

**Windows (PowerShell):**
```powershell
powershell -ex AllSigned -c "Invoke-RestMethod 'https://aka.ms/install-azd.ps1' | Invoke-Expression"
```

**macOS/Linux:**
```bash
curl -fsSL https://aka.ms/install-azd.sh | bash
```

**Verify Installation:**
```bash
azd version
```

### Other Requirements
- Azure subscription with appropriate permissions
- Docker Desktop (for local development)
- Git

## Quick Start with azd

### 1. Initialize and Login

```bash
# Login to Azure
azd auth login

# Initialize the project (if not already initialized)
azd init
```

### 2. Deploy Everything

```bash
# Provision infrastructure and deploy code
azd up
```

This single command will:
- ✅ Create all Azure resources (OpenAI, Cosmos DB, Container Apps, etc.)
- ✅ Build Docker images
- ✅ Push images to Azure Container Registry
- ✅ Deploy containers to Azure Container Apps
- ✅ Configure environment variables
- ✅ Output application URL

### 3. Access Your Application

After deployment completes, azd will display the application URL:
```
Endpoint: https://<your-app>.azurecontainerapps.io
```

## azd Commands Reference

### Deployment Commands

```bash
# Full deployment (infrastructure + code)
azd up

# Provision infrastructure only
azd provision

# Deploy code only (after infrastructure exists)
azd deploy

# Deploy specific service
azd deploy mcp
azd deploy app
```

### Environment Management

```bash
# Create a new environment
azd env new dev

# Select an environment
azd env select dev

# List environments
azd env list

# Set environment variables
azd env set AZURE_LOCATION eastus2
azd env set DISABLE_AUTH true

# View environment values
azd env get-values
```

### Monitoring and Management

```bash
# View deployment logs
azd monitor --logs

# Open Azure Portal for the resource group
azd monitor --portal

# View application endpoints
azd env get-values | grep URL
```

### Cleanup

```bash
# Delete all Azure resources
azd down

# Delete resources and local environment
azd down --purge
```

## Configuration

### Environment Variables

azd automatically reads from `.env` files. Create `.azure/<environment-name>/.env`:

```env
# Optional: Override default location
AZURE_LOCATION=eastus2

# Optional: Disable authentication for dev
DISABLE_AUTH=true

# Optional: Custom resource naming
AZURE_ENV_NAME=myworkshop
```

### Custom Parameters

You can override parameters during deployment:

```bash
azd up --parameter location=westus2
azd up --parameter environmentName=production
```

## Multi-Environment Deployment

### Development Environment

```bash
azd env new dev
azd env set AZURE_LOCATION eastus2
azd up
```

### Staging Environment

```bash
azd env new staging
azd env set AZURE_LOCATION eastus2
azd up
```

### Production Environment

```bash
azd env new prod
azd env set AZURE_LOCATION eastus2
azd env set DISABLE_AUTH false
azd up
```

### Switch Between Environments

```bash
# Deploy to dev
azd env select dev
azd deploy

# Deploy to prod
azd env select prod
azd deploy
```

## CI/CD with azd

### GitHub Actions

Create `.github/workflows/azure-dev.yml`:

```yaml
name: Azure Developer CLI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      AZURE_CLIENT_ID: ${{ vars.AZURE_CLIENT_ID }}
      AZURE_TENANT_ID: ${{ vars.AZURE_TENANT_ID }}
      AZURE_SUBSCRIPTION_ID: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      AZURE_ENV_NAME: ${{ vars.AZURE_ENV_NAME }}
      AZURE_LOCATION: ${{ vars.AZURE_LOCATION }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Install azd
        uses: Azure/setup-azd@v1.0.0

      - name: Log in with Azure (Federated Credentials)
        run: |
          azd auth login `
            --client-id "$Env:AZURE_CLIENT_ID" `
            --federated-credential-provider "github" `
            --tenant-id "$Env:AZURE_TENANT_ID"
        shell: pwsh

      - name: Provision Infrastructure
        run: azd provision --no-prompt

      - name: Deploy Application
        run: azd deploy --no-prompt
```

### Azure DevOps Pipeline

Create `azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: ubuntu-latest

variables:
  - group: azd-variables

steps:
  - task: AzureCLI@2
    displayName: Install azd
    inputs:
      azureSubscription: $(serviceConnection)
      scriptType: bash
      scriptLocation: inlineScript
      inlineScript: |
        curl -fsSL https://aka.ms/install-azd.sh | bash

  - task: AzureCLI@2
    displayName: Deploy with azd
    inputs:
      azureSubscription: $(serviceConnection)
      scriptType: bash
      scriptLocation: inlineScript
      inlineScript: |
        azd up --no-prompt
    env:
      AZURE_ENV_NAME: $(AZURE_ENV_NAME)
      AZURE_LOCATION: $(AZURE_LOCATION)
```

## Comparison: azd vs PowerShell Script

| Feature | azd | PowerShell Script |
|---------|-----|-------------------|
| **Ease of Use** | Single command (`azd up`) | Multiple steps |
| **Environment Management** | Built-in (`azd env`) | Manual |
| **State Management** | Automatic | Manual |
| **CI/CD Integration** | Native GitHub Actions support | Custom workflow |
| **Multi-region** | Easy with environments | Requires parameters |
| **Incremental Updates** | `azd deploy` | Partial support |
| **Learning Curve** | Simple commands | Azure CLI knowledge needed |

## Troubleshooting azd

### View Detailed Logs

```bash
azd up --debug
```

### Check Environment Configuration

```bash
azd env get-values
```

### Validate Infrastructure

```bash
azd provision --preview
```

### Reset Environment

```bash
azd down
rm -rf .azure/<env-name>
azd env new <env-name>
azd up
```

### Common Issues

#### Issue: "azd: command not found"
**Solution:** Reinstall azd or restart terminal

#### Issue: Docker build fails
**Solution:** Ensure Docker Desktop is running
```bash
docker ps
```

#### Issue: Authentication failed
**Solution:** Re-authenticate
```bash
azd auth login --use-device-code
```

#### Issue: Quota exceeded
**Solution:** Check Azure quotas in portal or request increase

## Advanced Configuration

### Custom Bicep Parameters

Edit `infra/main.azd.bicep` to add parameters:

```bicep
@description('Custom parameter')
param customValue string = 'default'
```

Set via environment:
```bash
azd env set CUSTOM_VALUE myvalue
```

### Hooks (Pre/Post Deployment)

Create `azure.yaml` hooks:

```yaml
name: openai-workshop
hooks:
  preprovision:
    shell: sh
    run: echo "Before provisioning"
  postdeploy:
    shell: sh
    run: |
      echo "After deployment"
      curl $APPLICATION_URL/health
```

### Custom Service Configuration

Edit `azure.yaml` to customize services:

```yaml
services:
  mcp:
    project: ./mcp
    language: python
    host: containerapp
    docker:
      path: ./Dockerfile
      context: ./
    env:
      CUSTOM_VAR: value
```

## Monitoring with azd

### Live Logs

```bash
# All services
azd monitor --logs

# Specific service
azd monitor --logs --service app
azd monitor --logs --service mcp

# Follow logs
azd monitor --logs --follow
```

### Open Azure Portal

```bash
azd monitor --portal
```

### Application Insights

```bash
azd monitor --overview
```

## Best Practices

1. **Use Environments**: Separate dev, staging, prod
   ```bash
   azd env new dev
   azd env new staging
   azd env new prod
   ```

2. **Set Defaults in .env**: Store common settings
   ```env
   AZURE_LOCATION=eastus2
   AZURE_ENV_NAME=workshop
   ```

3. **Version Control**: Commit `azure.yaml` and `infra/` directory
   - ✅ Commit: `azure.yaml`, `infra/`
   - ❌ Don't commit: `.azure/` directory

4. **Use CI/CD**: Automate with GitHub Actions or Azure DevOps

5. **Monitor Costs**: Use `azd monitor --portal` to check costs

## Next Steps

- **Customize Infrastructure**: Edit `infra/main.azd.bicep`
- **Add Services**: Update `azure.yaml`
- **Configure CI/CD**: Set up GitHub Actions
- **Enable Monitoring**: Add Application Insights
- **Scale Resources**: Adjust container app scaling in Bicep

## Resources

- [Azure Developer CLI Documentation](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- [azd GitHub Repository](https://github.com/Azure/azure-dev)
- [azd Templates](https://azure.github.io/awesome-azd/)
- [azd Community](https://github.com/Azure/azure-dev/discussions)
