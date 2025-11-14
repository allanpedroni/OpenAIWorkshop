# Azure Deployment Guide - OpenAI Workshop

This guide explains how to deploy the OpenAI Workshop application to Azure using Azure Developer CLI (azd).

## Prerequisites

1. **Azure Developer CLI (azd)** - [Install azd](https://aka.ms/azd-install)
2. **Azure CLI** - [Install Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli)
3. ~~**Docker Desktop**~~ - Not required! ACR builds images in the cloud

## Quick Start

### One-Command Deployment with azd up

```powershell
# Initialize azd environment (first time only)
azd env new agenticaiworkshop
azd env set AZURE_LOCATION eastus2

# Deploy everything - infrastructure and containers
azd up
```

That's it! `azd up` will:
1. ✅ Provision Azure infrastructure (Resource Group, OpenAI, Cosmos DB, ACR, etc.)
2. ✅ Build Docker images using **Azure Container Registry** (no local Docker needed!)
3. ✅ Deploy Container Apps with the built images

### Using ACR Remote Build

The deployment uses **ACR remote builds** (`docker.remote: true` in `azure.yaml`), which means:
- 🚀 **No Docker Desktop required** - images are built in Azure
- 🌐 **Faster builds** - builds happen in Azure data center
- 📦 **Direct to registry** - images go straight to ACR without local storage
- 🔧 **Consistent platform** - always builds for `linux/amd64`

## Deployment Architecture

The deployment creates:
- Resource Group (`rg-<env-name>`)
- Azure OpenAI Service (GPT-5-Chat, text-embedding-ada-002)
- Cosmos DB (NoSQL with 5 containers) - *infrastructure only, not connected to app yet*
- Container Registry (ACR) - used for remote builds
- Log Analytics Workspace
- Container Apps Environment
- MCP Service Container App
- Application Container App (FastAPI backend + React frontend)

## How Remote Builds Work

When you run `azd up`, the workflow is:

1. **Provision infrastructure** - Creates all Azure resources including ACR
2. **Package services** - Uploads source code to ACR
3. **ACR builds images** - ACR runs `docker build` in the cloud for both services
4. **Deploy Container Apps** - Creates Container Apps with the built images

The `azure.yaml` configuration uses `docker.remote: true` which tells azd to use ACR for building.

## Configuration Files

- `azure.yaml` - azd project configuration
- `infra/main.azd.bicep` - Main infrastructure template
- `infra/main.azd.bicepparam` - Parameters with environment variable mapping
- `infra/modules/*.bicep` - Modular resource definitions

## Environment Variables

After deployment, these are automatically set in your azd environment:

```bash
AZURE_OPENAI_ENDPOINT           # Azure OpenAI endpoint URL
AZURE_OPENAI_CHAT_DEPLOYMENT    # gpt-5-chat deployment name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT # text-embedding-ada-002 deployment name
AZURE_COSMOS_ENDPOINT           # Cosmos DB endpoint
AZURE_COSMOS_DATABASE_NAME      # Database name (contoso)
AZURE_CONTAINER_REGISTRY_NAME   # ACR name
APPLICATION_URL                 # Deployed application URL
MCP_SERVICE_URL                 # MCP service URL
```

View all environment variables:
```powershell
azd env get-values
```

## Monitoring and Management

### View Deployment Status
```powershell
azd monitor --overview
```

### Stream Container Logs
```powershell
azd monitor --logs
```

### View in Azure Portal
```powershell
azd show
```

### Update After Code Changes
```powershell
# Rebuild and redeploy containers only
./azd-deploy.ps1 -DeployOnly
```

### Clean Up Resources
```powershell
# Remove all resources
azd down

# Or use the script
./azd-deploy.ps1 -Clean
```

## Troubleshooting

### Issue: azd up fails during provisioning

**Solution**: Check the error message. Common issues:
- Insufficient Azure permissions
- Region doesn't support GPT-5-Chat (use `eastus2`)
- Resource naming conflicts

### Issue: Container App deployment fails

**Solution**: ACR remote builds can take time. Check ACR build status:
```powershell
$acrName = azd env get-value AZURE_CONTAINER_REGISTRY_NAME
az acr task list-runs --registry $acrName -o table
```

### Issue: Application doesn't connect to MCP service

**Solution**: Check Container App logs:
```powershell
azd monitor --logs
```

### Issue: Need to rebuild just one service

**Solution**: Use azd deploy with specific service:
```powershell
azd deploy app   # Rebuild and deploy just the application
azd deploy mcp   # Rebuild and deploy just the MCP service
```

## Resource Naming Convention

- Resource Group: `rg-<env-name>`
- OpenAI: `aiws-<token>-<env-name>-openai`
- Cosmos DB: `aiws-<token>-<env-name>-cosmos`
- ACR: `aiws<token><env-name>acr` (no hyphens)
- Container Apps: `aiws-<token>-mcp` and `aiws-<token>-app` (max 32 chars)
- Log Analytics: `aiws-<token>-<env-name>-logs`
- Container Apps Environment: `aiws-<token>-<env-name>-ca-env`

Where `<token>` is a unique 13-character string based on subscription ID and environment name.

## Security Considerations

1. **API Keys**: Stored as secrets in Container App configuration
2. **Container Registry**: Uses admin credentials (consider using Managed Identity in production)
3. **Network Security**: Container Apps have public ingress (consider VNet integration for production)
4. **Authentication**: Currently disabled (`DISABLE_AUTH=true`), enable for production

## Cost Estimation

Approximate monthly costs (East US 2):
- Azure OpenAI: ~$150-300 (depends on usage)
- Cosmos DB: ~$25-50 (depends on throughput)
- Container Apps: ~$30-60 (2 apps, 1 vCPU, 2GB RAM each)
- Container Registry: ~$5 (Basic tier)
- Log Analytics: ~$5-10 (depends on ingestion)

**Total**: ~$215-425/month

To minimize costs:
- Delete resources when not in use: `azd down`
- Use Azure's free tier and credits for development

## Next Steps

After successful deployment:

1. **Test the Application**: Visit the `APPLICATION_URL` from deployment output
2. **Test Agent Selection**: Use the dropdown to switch between 5 agent types
3. **Verify MCP Service**: The application should connect to MCP service automatically
4. **Check Cosmos DB**: State is persisted in the `workshop_agent_state_store` container

## Support

For issues or questions:
- Check [Azure Developer CLI docs](https://learn.microsoft.com/azure/developer/azure-developer-cli/)
- Review [Container Apps documentation](https://learn.microsoft.com/azure/container-apps/)
- See project README.md for application-specific guidance
