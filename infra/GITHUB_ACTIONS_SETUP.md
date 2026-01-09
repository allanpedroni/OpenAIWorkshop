# GitHub Actions CI/CD Setup Guide

This guide documents how to configure GitHub Actions for automated infrastructure deployment and container builds for the OpenAI Workshop project.

## Overview

The CI/CD pipeline uses:
- **OIDC Authentication** - No secrets stored in GitHub, uses federated identity
- **Remote Terraform State** - Shared state in Azure Storage for team collaboration
- **Environment-based Deployments** - Separate configs for dev, integration, prod

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         GitHub Actions                               │
├─────────────────────────────────────────────────────────────────────┤
│  orchestrate.yml                                                     │
│    ├── preflight (enable storage access)                            │
│    ├── docker-application.yml (build backend image)                 │
│    ├── docker-mcp.yml (build MCP service image)                     │
│    ├── infrastructure.yml (Terraform deploy)                        │
│    ├── update-containers.yml (refresh running apps)                 │
│    └── destroy.yml (optional cleanup)                               │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ OIDC (no secrets)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Azure                                        │
├─────────────────────────────────────────────────────────────────────┤
│  ├── App Registration (GitHub-Actions-OpenAIWorkshop)               │
│  │     └── Federated Credentials (main, int-agentic, PRs)           │
│  ├── Storage Account (Terraform state)                              │
│  ├── Container Registry (Docker images)                             │
│  └── Container Apps (MCP + Backend)                                 │
└─────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Azure CLI installed and logged in
- Contributor access to the Azure subscription
- Admin access to the GitHub repository

---

## Step 1: Create Azure App Registration for OIDC

Run the setup script:

```powershell
.\scripts\setup-github-oidc.ps1
```

Or manually:

```powershell
# Variables
$AppName = "GitHub-Actions-OpenAIWorkshop"
$GitHubOrg = "YOUR_GITHUB_ORG"        # e.g., "contoso"
$GitHubRepo = "YOUR_GITHUB_REPO"      # e.g., "OpenAIWorkshop"

# Create App Registration
$app = az ad app create --display-name $AppName --query appId -o tsv

# Create Service Principal
az ad sp create --id $app

# Get IDs
$TenantId = az account show --query tenantId -o tsv
$SubscriptionId = az account show --query id -o tsv
$ObjectId = az ad sp show --id $app --query id -o tsv

Write-Host "Client ID: $app"
Write-Host "Tenant ID: $TenantId"
Write-Host "Subscription ID: $SubscriptionId"
```

## Step 2: Configure Federated Credentials

Create federated credentials for each branch/environment:

```powershell
$AppId = "YOUR_APP_ID"  # From Step 1

# Main branch (prod)
az ad app federated-credential create --id $AppId --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
}'

# Integration branch
az ad app federated-credential create --id $AppId --parameters '{
    "name": "github-int-agentic",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:ref:refs/heads/int-agentic",
    "audiences": ["api://AzureADTokenExchange"]
}'

# Pull Requests
az ad app federated-credential create --id $AppId --parameters '{
    "name": "github-pullrequests",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:YOUR_ORG/YOUR_REPO:pull_request",
    "audiences": ["api://AzureADTokenExchange"]
}'
```

## Step 3: Assign Azure Roles

```powershell
$AppId = "YOUR_APP_ID"
$SubscriptionId = "YOUR_SUBSCRIPTION_ID"

# Contributor - for creating resources
az role assignment create `
    --assignee $AppId `
    --role "Contributor" `
    --scope "/subscriptions/$SubscriptionId"

# User Access Administrator - for role assignments
az role assignment create `
    --assignee $AppId `
    --role "User Access Administrator" `
    --scope "/subscriptions/$SubscriptionId"
```

## Step 4: Create Terraform State Storage

```powershell
$RG = "rg-tfstate"
$ACCOUNT = "sttfstateoaiworkshop"  # Must be globally unique
$CONTAINER = "tfstate"
$LOCATION = "eastus2"

# Create resources
az group create --name $RG --location $LOCATION
az storage account create `
    --name $ACCOUNT `
    --resource-group $RG `
    --location $LOCATION `
    --sku Standard_LRS `
    --allow-blob-public-access false

az storage container create `
    --name $CONTAINER `
    --account-name $ACCOUNT `
    --auth-mode login

# Grant access to GitHub Actions service principal
$STORAGE_ID = az storage account show --name $ACCOUNT --resource-group $RG --query id -o tsv
az role assignment create `
    --assignee $AppId `
    --role "Storage Blob Data Contributor" `
    --scope $STORAGE_ID
```

## Step 5: Configure GitHub Repository Variables

Go to **GitHub → Repository → Settings → Secrets and Variables → Actions → Variables**

### Required Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `AZURE_CLIENT_ID` | App Registration Client ID | `1d34c51d-9d49-48f3-9e48-6a0f099c5f03` |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | `0fbe7234-45ea-498b-b7e4-1a8b2d3be4d9` |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | `840b5c5c-3f4a-459a-94fc-6bad2a969f9d` |
| `TFSTATE_RG` | Resource group for TF state | `rg-tfstate` |
| `TFSTATE_ACCOUNT` | Storage account name | `sttfstateoaiworkshop` |
| `TFSTATE_CONTAINER` | Blob container name | `tfstate` |
| `ACR_NAME` | Azure Container Registry name | `acropenaiworkshop002` |
| `PROJECT_NAME` | Project identifier | `OpenAIWorkshop` |
| `ITERATION` | Deployment iteration | `002` |
| `AZ_REGION` | Azure region | `eastus2` |

### Optional Environment-Specific Variables

Create GitHub Environments (`dev`, `integration`, `prod`) for environment-specific overrides:

| Environment | Variable | Value |
|-------------|----------|-------|
| `prod` | `AZ_REGION` | `eastus` |
| `prod` | `ITERATION` | `001` |

---

## Workflow Triggers

| Workflow | Trigger | What it does |
|----------|---------|--------------|
| `orchestrate.yml` | Push to main/int-agentic, PRs, manual | Full deployment pipeline |
| `infrastructure.yml` | Called by orchestrate | Terraform plan/apply |
| `docker-application.yml` | Called by orchestrate | Build backend container |
| `docker-mcp.yml` | Called by orchestrate | Build MCP container |
| `update-containers.yml` | Called by orchestrate | Refresh Container Apps |
| `destroy.yml` | Called by orchestrate (dev only) | Terraform destroy |

## Branch to Environment Mapping

| Branch | Environment | Auto-destroy |
|--------|-------------|--------------|
| `main` | `prod` | ❌ No |
| `int-agentic` | `integration` | ❌ No |
| `tjs-infra-as-code` | `dev` | ✅ Yes |
| Other branches | `dev` | Depends on config |

---

## Manual Deployment (Local)

For local development without GitHub Actions:

```powershell
cd infra/terraform

# Deploy with local state (default)
./deploy.ps1 -Environment dev

# Deploy with remote state (team collaboration)
$env:TFSTATE_RG = "rg-tfstate"
$env:TFSTATE_ACCOUNT = "sttfstateoaiworkshop"
$env:TFSTATE_CONTAINER = "tfstate"
$env:TFSTATE_KEY = "local-dev.tfstate"
./deploy.ps1 -Environment dev -RemoteBackend
```

---

## Troubleshooting

### OIDC Login Fails
- Verify federated credential subject matches exactly: `repo:ORG/REPO:ref:refs/heads/BRANCH`
- Check the App Registration has a service principal created
- Ensure role assignments are at subscription scope

### Terraform State Lock
- State is locked during operations
- If stuck, check Azure Storage for lease on the state blob
- Break lease: `az storage blob lease break --blob-name STATE_FILE --container-name tfstate --account-name ACCOUNT`

### Container App Not Updating
- Images are pushed but Container Apps use cached images
- The `update-containers.yml` workflow forces a refresh
- Manual: `az containerapp update --name APP_NAME --resource-group RG --image NEW_IMAGE`

### ACR Authentication Fails
- Ensure service principal has `AcrPush` role on the ACR
- OIDC login must happen before `az acr login`

---

## Security Notes

1. **No Secrets in GitHub** - OIDC eliminates the need for stored credentials
2. **Scoped Permissions** - Federated credentials are branch-specific
3. **Private ACR** - Container registry is not publicly accessible
4. **State Encryption** - Terraform state is encrypted at rest in Azure Storage
5. **Environment Protection** - Add required reviewers for `prod` environment in GitHub

---

## Current Configuration

| Setting | Value |
|---------|-------|
| App Registration | `GitHub-Actions-OpenAIWorkshop` |
| Client ID | `1d34c51d-9d49-48f3-9e48-6a0f099c5f03` |
| Tenant ID | `0fbe7234-45ea-498b-b7e4-1a8b2d3be4d9` |
| Subscription ID | `840b5c5c-3f4a-459a-94fc-6bad2a969f9d` |
| TF State Storage | `sttfstateoaiworkshop` |
| TF State Container | `tfstate` |
| TF State RG | `rg-tfstate` |

---

## Files Reference

```
.github/workflows/
├── orchestrate.yml          # Main orchestration workflow
├── infrastructure.yml       # Terraform deployment
├── docker-application.yml   # Backend container build
├── docker-mcp.yml          # MCP container build
├── update-containers.yml    # Container App refresh
├── destroy.yml             # Infrastructure teardown
└── readme.md               # Workflow documentation

infra/
├── GITHUB_ACTIONS_SETUP.md  # This file
├── scripts/
│   └── setup-github-oidc.ps1  # OIDC setup script
└── terraform/
    ├── deploy.ps1           # Local deployment script
    ├── providers.tf         # Terraform providers
    ├── providers.tf.local   # Local backend config
    ├── providers.tf.remote  # Remote backend config
    └── *.tfvars            # Environment variables
```
