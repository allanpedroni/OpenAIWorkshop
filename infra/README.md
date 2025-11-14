# Azure Infrastructure Deployment

This directory contains Bicep templates and deployment scripts for deploying the OpenAI Workshop application to Azure.

## Architecture

The deployment creates the following Azure resources:

- **Azure OpenAI Service**: GPT-5-Chat (2025-10-03) and text-embedding-ada-002 models
- **Azure Cosmos DB**: NoSQL database with 5 containers (Customers, Subscriptions, Products, Promotions, Agent State)
- **Azure Container Registry**: Docker image registry for application containers
- **Azure Container Apps**: 
  - MCP Service (Model Context Protocol server)
  - Application (FastAPI backend + React frontend)
- **Log Analytics Workspace**: Monitoring and logging for Container Apps

## Directory Structure

```
infra/
├── main.bicep                          # Main orchestrator template
├── deploy.ps1                          # PowerShell deployment script
├── parameters/                         # Environment-specific parameters
│   ├── dev.bicepparam
│   ├── staging.bicepparam
│   └── prod.bicepparam
└── modules/                            # Modular Bicep templates
    ├── openai.bicep                    # Azure OpenAI deployment
    ├── cosmosdb.bicep                  # Cosmos DB with containers
    ├── container-registry.bicep        # Container Registry
    ├── log-analytics.bicep             # Log Analytics workspace
    ├── container-apps-environment.bicep # Container Apps environment
    ├── mcp-service.bicep               # MCP service container
    └── application.bicep               # Application container
```

## Prerequisites

1. **Azure CLI**: Install from https://aka.ms/azure-cli
2. **Docker**: Required for building images
3. **PowerShell 7+**: For running deployment scripts
4. **Azure Subscription**: With appropriate permissions

### Login to Azure

```powershell
az login
az account set --subscription <subscription-id>
```

## Deployment Options

### Option 1: Full Deployment (Infrastructure + Containers)

Deploy everything including building and pushing Docker images:

```powershell
cd infra
./deploy.ps1 -Environment dev
```

### Option 2: Infrastructure Only

Deploy only the Azure infrastructure without building containers:

```powershell
./deploy.ps1 -Environment dev -InfraOnly
```

### Option 3: Skip Container Builds

Deploy infrastructure and restart containers with existing images:

```powershell
./deploy.ps1 -Environment dev -SkipBuild
```

### Option 4: Custom Parameters

```powershell
./deploy.ps1 -Environment staging -Location eastus -BaseName my-workshop
```

## Environment Parameters

Three environments are pre-configured:

- **dev**: Development environment with minimal resources
- **staging**: Staging environment for testing
- **prod**: Production environment with high availability

Edit parameter files in `parameters/` directory to customize:

```bicep
// parameters/dev.bicepparam
using '../main.bicep'

param location = 'eastus2'
param environmentName = 'dev'
param baseName = 'openai-workshop'
param tags = { ... }
```

## Manual Deployment with Bicep

### Deploy with default parameters:

```bash
az deployment sub create \
  --location eastus2 \
  --template-file main.bicep \
  --parameters location=eastus2 environmentName=dev baseName=openai-workshop
```

### Deploy with parameter file:

```bash
az deployment sub create \
  --location eastus2 \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam
```

## Building and Pushing Container Images

### MCP Service:

```powershell
cd mcp
docker build -t <acr-name>.azurecr.io/mcp-service:latest -f Dockerfile .
docker push <acr-name>.azurecr.io/mcp-service:latest
```

### Application:

```powershell
cd agentic_ai/applications
docker build -t <acr-name>.azurecr.io/workshop-app:latest -f Dockerfile .
docker push <acr-name>.azurecr.io/workshop-app:latest
```

## Post-Deployment

After deployment, the script outputs:

- **Application URL**: Public URL for the web application
- **MCP Service URL**: Internal URL for MCP service
- **Resource Group**: Name of the resource group

### Access the Application:

The application URL will be in the format:
```
https://<basename>-<env>-app.<region>.azurecontainerapps.io
```

### View Logs:

```powershell
# Application logs
az containerapp logs show \
  --name openai-workshop-dev-app \
  --resource-group openai-workshop-dev-rg \
  --follow

# MCP Service logs
az containerapp logs show \
  --name openai-workshop-dev-mcp \
  --resource-group openai-workshop-dev-rg \
  --follow
```

### Update Container Apps:

After pushing new images, restart the containers:

```powershell
az containerapp revision restart \
  --resource-group openai-workshop-dev-rg \
  --name openai-workshop-dev-app \
  --revision latest
```

## Scaling Configuration

Both container apps are configured with auto-scaling:

- **MCP Service**: 1-3 replicas based on HTTP requests
- **Application**: 1-5 replicas based on HTTP requests (20 concurrent max)

Modify scaling in `modules/mcp-service.bicep` or `modules/application.bicep`:

```bicep
scale: {
  minReplicas: 1
  maxReplicas: 10
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
```

## Security Considerations

1. **Secrets Management**: Keys are stored as Container App secrets
2. **Network Security**: Container Apps use internal networking
3. **Authentication**: Azure AD integration supported (set DISABLE_AUTH=false)
4. **CORS**: Frontend CORS policies configured in application.bicep

## Troubleshooting

### Issue: Container fails to start

Check logs:
```powershell
az containerapp logs show --name <app-name> --resource-group <rg-name> --follow
```

### Issue: Cannot push to ACR

Login to ACR:
```powershell
az acr login --name <acr-name>
```

### Issue: Deployment fails

Validate Bicep templates:
```powershell
az deployment sub validate \
  --location eastus2 \
  --template-file main.bicep \
  --parameters parameters/dev.bicepparam
```

### Issue: OpenAI quota limits

Check quotas in Azure Portal:
```
Azure OpenAI > Quotas > View quotas
```

## Cost Optimization

- Use **dev** environment for development (smaller SKUs)
- Delete resources when not needed:
  ```powershell
  az group delete --name openai-workshop-dev-rg --yes
  ```
- Monitor costs in Azure Cost Management

## CI/CD Integration

### GitHub Actions Example:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Deploy Infrastructure
        run: |
          cd infra
          ./deploy.ps1 -Environment prod
```

## Additional Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Azure Cosmos DB Documentation](https://learn.microsoft.com/azure/cosmos-db/)

## Support

For issues or questions:
1. Check the main project README
2. Review Azure activity logs in the portal
3. Check Container App logs with `az containerapp logs`
