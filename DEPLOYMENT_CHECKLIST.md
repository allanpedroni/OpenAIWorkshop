# Azure Deployment Checklist

Use this checklist to ensure a smooth deployment of the OpenAI Workshop to Azure.

## Pre-Deployment

### Environment Setup
- [ ] Azure CLI installed and updated (`az --version`)
- [ ] Docker Desktop installed and running
- [ ] PowerShell 7+ installed
- [ ] Git installed and repository cloned
- [ ] Logged into Azure (`az login`)
- [ ] Correct subscription selected (`az account set`)

### Azure Prerequisites
- [ ] Subscription has Owner or Contributor role
- [ ] Azure OpenAI service access approved
- [ ] Resource providers registered:
  ```powershell
  az provider register --namespace Microsoft.App
  az provider register --namespace Microsoft.CognitiveServices
  az provider register --namespace Microsoft.DocumentDB
  az provider register --namespace Microsoft.ContainerRegistry
  az provider register --namespace Microsoft.OperationalInsights
  ```
- [ ] Sufficient quotas for:
  - [ ] Azure OpenAI (GPT-4)
  - [ ] Container Apps (2 apps minimum)
  - [ ] Cosmos DB (1 account)

### Configuration Review
- [ ] Review `infra/parameters/dev.bicepparam`
- [ ] Update `location` if needed (default: eastus2)
- [ ] Update `baseName` if needed (default: openai-workshop)
- [ ] Update `tags` as appropriate
- [ ] Review environment variables in Bicep modules

## Validation Phase

### Template Validation
- [ ] Navigate to infra directory: `cd infra`
- [ ] Validate Bicep syntax:
  ```powershell
  az deployment sub validate `
    --location eastus2 `
    --template-file main.bicep `
    --parameters parameters/dev.bicepparam
  ```
- [ ] Review validation output for warnings/errors
- [ ] Fix any issues before proceeding

### Local Docker Build Test
- [ ] Test MCP service build:
  ```powershell
  cd mcp
  docker build -t mcp-service:test -f Dockerfile .
  ```
- [ ] Test application build:
  ```powershell
  cd agentic_ai/applications
  docker build -t workshop-app:test -f Dockerfile .
  ```
- [ ] Verify both builds complete successfully

## Deployment Phase

### Option 1: Automated Deployment (Recommended)
- [ ] Run deployment script:
  ```powershell
  cd infra
  ./deploy.ps1 -Environment dev
  ```
- [ ] Monitor deployment progress (takes 15-30 minutes)
- [ ] Wait for "Deployment Complete!" message
- [ ] Note the Application URL from output

### Option 2: Manual Step-by-Step Deployment
- [ ] Deploy infrastructure:
  ```powershell
  az deployment sub create `
    --location eastus2 `
    --template-file main.bicep `
    --parameters parameters/dev.bicepparam `
    --name "workshop-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
  ```
- [ ] Save deployment outputs to file:
  ```powershell
  az deployment sub show --name <deployment-name> --query properties.outputs -o json > outputs.json
  ```
- [ ] Get ACR name from outputs
- [ ] Login to ACR:
  ```powershell
  az acr login --name <acr-name>
  ```
- [ ] Build and push MCP service:
  ```powershell
  cd mcp
  docker build -t <acr-name>.azurecr.io/mcp-service:latest .
  docker push <acr-name>.azurecr.io/mcp-service:latest
  ```
- [ ] Build and push application:
  ```powershell
  cd agentic_ai/applications
  docker build -t <acr-name>.azurecr.io/workshop-app:latest .
  docker push <acr-name>.azurecr.io/workshop-app:latest
  ```
- [ ] Restart Container Apps:
  ```powershell
  az containerapp revision restart --resource-group <rg-name> --name <mcp-name> --revision latest
  az containerapp revision restart --resource-group <rg-name> --name <app-name> --revision latest
  ```

## Post-Deployment Verification

### Resource Verification
- [ ] List deployed resources:
  ```powershell
  az resource list --resource-group openai-workshop-dev-rg --output table
  ```
- [ ] Verify Azure OpenAI deployment:
  ```powershell
  az cognitiveservices account show `
    --name openai-workshop-dev-openai `
    --resource-group openai-workshop-dev-rg
  ```
- [ ] Verify Cosmos DB account:
  ```powershell
  az cosmosdb show `
    --name openai-workshop-dev-cosmos `
    --resource-group openai-workshop-dev-rg
  ```
- [ ] Verify Container Registry:
  ```powershell
  az acr show `
    --name <acr-name> `
    --resource-group openai-workshop-dev-rg
  ```
- [ ] List container apps:
  ```powershell
  az containerapp list `
    --resource-group openai-workshop-dev-rg `
    --output table
  ```

### Container App Health
- [ ] Check MCP service status:
  ```powershell
  az containerapp show `
    --name openai-workshop-dev-mcp `
    --resource-group openai-workshop-dev-rg `
    --query "properties.runningStatus"
  ```
- [ ] Check application status:
  ```powershell
  az containerapp show `
    --name openai-workshop-dev-app `
    --resource-group openai-workshop-dev-rg `
    --query "properties.runningStatus"
  ```
- [ ] Verify both show "Running"
- [ ] Check replica count:
  ```powershell
  az containerapp replica list `
    --name openai-workshop-dev-app `
    --resource-group openai-workshop-dev-rg
  ```

### Log Verification
- [ ] View MCP service logs:
  ```powershell
  az containerapp logs show `
    --name openai-workshop-dev-mcp `
    --resource-group openai-workshop-dev-rg `
    --tail 50
  ```
- [ ] View application logs:
  ```powershell
  az containerapp logs show `
    --name openai-workshop-dev-app `
    --resource-group openai-workshop-dev-rg `
    --tail 50
  ```
- [ ] Check for startup errors or warnings
- [ ] Verify "Uvicorn running" message in logs

### Application Testing
- [ ] Open application URL in browser
- [ ] Verify React frontend loads
- [ ] Check agent selector dropdown appears
- [ ] Verify 5 agents are listed:
  - [ ] Single Agent
  - [ ] Handoff Multi-Domain Agent
  - [ ] Magentic Group
  - [ ] Reflection Agent
  - [ ] Reflection Workflow Agent
- [ ] Test chat functionality:
  - [ ] Enter a simple message
  - [ ] Verify streaming response
  - [ ] Check for tool call execution
- [ ] Test agent switching:
  - [ ] Select different agent
  - [ ] Verify success notification
  - [ ] Test chat with new agent
- [ ] Check browser console for errors (F12)

### Connectivity Testing
- [ ] Test backend API endpoints:
  ```powershell
  # Get agents list
  curl https://<app-url>/agents
  
  # Health check
  curl https://<app-url>/
  ```
- [ ] Verify MCP service responds (internal, may need Container App exec):
  ```powershell
  az containerapp exec `
    --name openai-workshop-dev-app `
    --resource-group openai-workshop-dev-rg `
    --command "curl http://openai-workshop-dev-mcp:8000"
  ```
- [ ] Test WebSocket connection (browser DevTools → Network → WS)

### Data Verification
- [ ] Open Cosmos DB in Azure Portal
- [ ] Navigate to Data Explorer
- [ ] Verify containers exist:
  - [ ] Customers
  - [ ] Subscriptions
  - [ ] Products
  - [ ] Promotions
  - [ ] workshop_agent_state_store
- [ ] Check that agent state is being written during chat

### Monitoring Setup
- [ ] Open Log Analytics workspace in Azure Portal
- [ ] Run test queries:
  ```kql
  ContainerAppConsoleLogs_CL
  | where TimeGenerated > ago(1h)
  | where ContainerAppName_s == "openai-workshop-dev-app"
  | order by TimeGenerated desc
  | take 100
  ```
- [ ] Verify logs are flowing
- [ ] Create custom dashboard (optional)
- [ ] Set up alerts (optional):
  - [ ] Container restart alert
  - [ ] High error rate alert
  - [ ] Slow response time alert

## Security Review

### Authentication
- [ ] Verify DISABLE_AUTH is set correctly (true for dev, false for prod)
- [ ] If authentication enabled:
  - [ ] AAD_TENANT_ID is set
  - [ ] MCP_API_AUDIENCE is configured
  - [ ] Test login flow

### Secrets Management
- [ ] Verify secrets are not in logs:
  ```powershell
  az containerapp logs show --name <app-name> --resource-group <rg-name> | Select-String "key|password|secret"
  ```
- [ ] Check secrets are properly configured:
  ```powershell
  az containerapp show `
    --name openai-workshop-dev-app `
    --resource-group openai-workshop-dev-rg `
    --query "properties.configuration.secrets"
  ```
- [ ] Verify secrets are marked as secretRef in env vars

### Network Security
- [ ] Verify application ingress is external
- [ ] Verify MCP service ingress is internal (or no external ingress)
- [ ] Check CORS configuration allows frontend origin
- [ ] Review NSG rules (if custom networking)

## Performance Baseline

### Load Testing (Optional)
- [ ] Run basic load test:
  ```powershell
  # Use Azure Load Testing or Apache Bench
  ab -n 100 -c 10 https://<app-url>/
  ```
- [ ] Monitor CPU/Memory usage in Container Apps
- [ ] Verify auto-scaling triggers correctly
- [ ] Check response times are acceptable

### Optimization Review
- [ ] Review container resource allocations
- [ ] Check Cosmos DB RU consumption
- [ ] Verify OpenAI API latency
- [ ] Review cold start times

## Documentation

### Update Internal Docs
- [ ] Document application URL
- [ ] Document resource group name
- [ ] Document ACR name
- [ ] Save deployment outputs
- [ ] Update team wiki/confluence

### Knowledge Transfer
- [ ] Share deployment checklist with team
- [ ] Schedule walkthrough session
- [ ] Document any custom configurations
- [ ] Create runbook for common operations

## Rollback Plan

### Prepare Rollback
- [ ] Document previous working state
- [ ] Save backup of configuration
- [ ] Test rollback procedure:
  ```powershell
  # Redeploy previous revision
  az containerapp revision activate `
    --resource-group <rg-name> `
    --name <app-name> `
    --revision <previous-revision-name>
  ```
- [ ] Document rollback contacts

## Sign-Off

### Development Team
- [ ] Application deployed successfully
- [ ] All features working as expected
- [ ] Performance meets requirements
- [ ] Logs and monitoring configured

### DevOps Team
- [ ] Infrastructure deployed correctly
- [ ] All resources created
- [ ] Monitoring and alerts set up
- [ ] Backup and DR plan in place (if applicable)

### Security Team
- [ ] Security review completed
- [ ] Secrets properly managed
- [ ] Network security configured
- [ ] Compliance requirements met (if applicable)

## Post-Deployment Actions

### Immediate (Day 1)
- [ ] Monitor logs for first 24 hours
- [ ] Check for any errors or warnings
- [ ] Verify auto-scaling works as expected
- [ ] Respond to any user feedback

### Short-term (Week 1)
- [ ] Review cost management dashboard
- [ ] Optimize resource allocations if needed
- [ ] Create additional alerts based on observed patterns
- [ ] Document lessons learned

### Long-term (Month 1)
- [ ] Review usage patterns
- [ ] Optimize costs based on actual usage
- [ ] Plan for scaling requirements
- [ ] Schedule maintenance windows

## Troubleshooting Reference

### If Container Won't Start
1. Check logs: `az containerapp logs show`
2. Verify environment variables
3. Check secrets are configured
4. Verify image exists in ACR
5. Review Dockerfile and requirements.txt

### If Application Responds Slowly
1. Check replica count
2. Review Cosmos DB RU consumption
3. Check OpenAI API latency
4. Monitor CPU/Memory usage
5. Review network latency

### If Chat Doesn't Work
1. Check WebSocket connection in browser DevTools
2. Verify MCP service is running
3. Check agent module is loaded correctly
4. Review backend logs for errors
5. Test API endpoints directly

### If Data Not Persisting
1. Verify Cosmos DB connection string
2. Check Cosmos DB keys are valid
3. Review permissions on Cosmos DB
4. Check container names match code
5. Verify data is written to correct container

## Emergency Contacts

- **Azure Support**: https://portal.azure.com/#blade/Microsoft_Azure_Support/HelpAndSupportBlade
- **Team Lead**: [Name]
- **DevOps Lead**: [Name]
- **On-Call**: [Contact Info]

---

## Deployment Completion

**Date**: _________________

**Deployed By**: _________________

**Environment**: [ ] Dev [ ] Staging [ ] Prod

**Application URL**: _________________

**Resource Group**: _________________

**Notes**: _____________________________________________________

_____________________________________________________________

**Sign-off**: _________________ Date: _________________
