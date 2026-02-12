# GitHub Actions OIDC Setup Script for OpenAI Workshop
# This script creates an Azure App Registration with federated credentials for GitHub Actions

param(
    [Parameter(Mandatory=$false)]
    [string]$AppName = "GitHub-Actions-OpenAIWorkshop",
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubOrg,
    
    [Parameter(Mandatory=$true)]
    [string]$GitHubRepo,
    
    [Parameter(Mandatory=$false)]
    [string[]]$Branches = @("main", "int-agentic"),
    
    [Parameter(Mandatory=$false)]
    [switch]$IncludePullRequests = $true,

    # If your GitHub org/repo uses a customized OIDC subject claim template with
    # numeric IDs (repository_owner_id / repository_id), set these values.
    # You can find them via the GitHub API: GET /repos/{owner}/{repo}
    # ("owner.id" = OwnerID, "id" = RepoID).
    [Parameter(Mandatory=$false)]
    [string]$GitHubOwnerID,

    [Parameter(Mandatory=$false)]
    [string]$GitHubRepoID,
    
    [Parameter(Mandatory=$false)]
    [switch]$SetupTerraformState = $true,
    
    [Parameter(Mandatory=$false)]
    [string]$TerraformStateRG = "rg-tfstate",
    
    [Parameter(Mandatory=$false)]
    [string]$TerraformStateAccount = "sttfstateoaiworkshop",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus2"
)

$ErrorActionPreference = 'Stop'

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "GitHub Actions OIDC Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "GitHub Org:  $GitHubOrg" -ForegroundColor Yellow
Write-Host "GitHub Repo: $GitHubRepo" -ForegroundColor Yellow
Write-Host "Branches:    $($Branches -join ', ')" -ForegroundColor Yellow
Write-Host ""

# Get current Azure context
$TenantId = (az account show --query tenantId -o tsv)
$SubscriptionId = (az account show --query id -o tsv)

Write-Host "Azure Tenant:       $TenantId" -ForegroundColor Gray
Write-Host "Azure Subscription: $SubscriptionId" -ForegroundColor Gray
Write-Host ""

# ============================================
# Step 1: Create App Registration
# ============================================
Write-Host "[1/5] Creating App Registration..." -ForegroundColor Green

$existingApp = az ad app list --display-name $AppName --query "[0].appId" -o tsv 2>$null

if ($existingApp) {
    Write-Host "  App Registration already exists: $existingApp" -ForegroundColor Yellow
    $AppId = $existingApp
} else {
    $AppId = az ad app create --display-name $AppName --query appId -o tsv
    Write-Host "  Created App Registration: $AppId" -ForegroundColor Green
}

# ============================================
# Step 2: Create Service Principal
# ============================================
Write-Host "[2/5] Creating Service Principal..." -ForegroundColor Green

$existingSp = az ad sp show --id $AppId --query id -o tsv 2>$null

if ($existingSp) {
    Write-Host "  Service Principal already exists" -ForegroundColor Yellow
} else {
    az ad sp create --id $AppId | Out-Null
    Write-Host "  Created Service Principal" -ForegroundColor Green
}

# ============================================
# Step 3: Create Federated Credentials
# ============================================
Write-Host "[3/5] Creating Federated Credentials..." -ForegroundColor Green

$AppObjectId = az ad app show --id $AppId --query id -o tsv

# Determine subject format based on whether numeric IDs are provided.
# GitHub orgs/repos with a customized OIDC subject claim template use:
#   repository_owner_id:<owner_id>:repository_id:<repo_id>:ref:refs/heads/<branch>
# The default (non-customized) format is:
#   repo:<org>/<repo>:ref:refs/heads/<branch>
$useNumericSubject = ($GitHubOwnerID -and $GitHubRepoID)
if ($useNumericSubject) {
    Write-Host "Using numeric subject claim format (repository_owner_id / repository_id)" -ForegroundColor Cyan
} else {
    Write-Host "Using default subject claim format (repo:org/repo)" -ForegroundColor Cyan
}

# Create credential for each branch
foreach ($branch in $Branches) {
    $credName = "github-$($branch -replace '/', '-')"
    if ($useNumericSubject) {
        $subject = "repository_owner_id:${GitHubOwnerID}:repository_id:${GitHubRepoID}:ref:refs/heads/$branch"
    } else {
        $subject = "repo:${GitHubOrg}/${GitHubRepo}:ref:refs/heads/$branch"
    }
    
    $existing = az ad app federated-credential list --id $AppObjectId --query "[?name=='$credName'].name" -o tsv 2>$null
    
    if ($existing) {
        Write-Host "  Credential '$credName' already exists" -ForegroundColor Yellow
    } else {
        $credParams = @{
            name = $credName
            issuer = "https://token.actions.githubusercontent.com"
            subject = $subject
            audiences = @("api://AzureADTokenExchange")
        } | ConvertTo-Json -Compress
        
        az ad app federated-credential create --id $AppObjectId --parameters $credParams | Out-Null
        Write-Host "  Created credential for branch: $branch" -ForegroundColor Green
    }
}

# Create credential for pull requests
if ($IncludePullRequests) {
    $prCredName = "github-pullrequests"
    if ($useNumericSubject) {
        $prSubject = "repository_owner_id:${GitHubOwnerID}:repository_id:${GitHubRepoID}:pull_request"
    } else {
        $prSubject = "repo:${GitHubOrg}/${GitHubRepo}:pull_request"
    }
    
    $existing = az ad app federated-credential list --id $AppObjectId --query "[?name=='$prCredName'].name" -o tsv 2>$null
    
    if ($existing) {
        Write-Host "  Credential '$prCredName' already exists" -ForegroundColor Yellow
    } else {
        $prCredParams = @{
            name = $prCredName
            issuer = "https://token.actions.githubusercontent.com"
            subject = $prSubject
            audiences = @("api://AzureADTokenExchange")
        } | ConvertTo-Json -Compress
        
        az ad app federated-credential create --id $AppObjectId --parameters $prCredParams | Out-Null
        Write-Host "  Created credential for pull requests" -ForegroundColor Green
    }
}

# ============================================
# Step 4: Assign Azure Roles
# ============================================
Write-Host "[4/5] Assigning Azure Roles..." -ForegroundColor Green

$roles = @("Contributor", "User Access Administrator")

foreach ($role in $roles) {
    $existing = az role assignment list --assignee $AppId --role $role --scope "/subscriptions/$SubscriptionId" --query "[0].id" -o tsv 2>$null
    
    if ($existing) {
        Write-Host "  Role '$role' already assigned" -ForegroundColor Yellow
    } else {
        az role assignment create `
            --assignee $AppId `
            --role $role `
            --scope "/subscriptions/$SubscriptionId" | Out-Null
        Write-Host "  Assigned role: $role" -ForegroundColor Green
    }
}

# ============================================
# Step 5: Setup Terraform State Storage
# ============================================
if ($SetupTerraformState) {
    Write-Host "[5/5] Setting up Terraform State Storage..." -ForegroundColor Green
    
    # Create resource group
    $rgExists = az group exists --name $TerraformStateRG
    if ($rgExists -eq "false") {
        az group create --name $TerraformStateRG --location $Location | Out-Null
        Write-Host "  Created resource group: $TerraformStateRG" -ForegroundColor Green
    } else {
        Write-Host "  Resource group exists: $TerraformStateRG" -ForegroundColor Yellow
    }
    
    # Create storage account
    $storageExists = az storage account show --name $TerraformStateAccount --resource-group $TerraformStateRG --query name -o tsv 2>$null
    if (-not $storageExists) {
        az storage account create `
            --name $TerraformStateAccount `
            --resource-group $TerraformStateRG `
            --location $Location `
            --sku Standard_LRS `
            --allow-blob-public-access false | Out-Null
        Write-Host "  Created storage account: $TerraformStateAccount" -ForegroundColor Green
    } else {
        Write-Host "  Storage account exists: $TerraformStateAccount" -ForegroundColor Yellow
    }
    
    # Create container
    $containerExists = az storage container exists --name tfstate --account-name $TerraformStateAccount --auth-mode login --query exists -o tsv 2>$null
    if ($containerExists -ne "true") {
        az storage container create --name tfstate --account-name $TerraformStateAccount --auth-mode login | Out-Null
        Write-Host "  Created container: tfstate" -ForegroundColor Green
    } else {
        Write-Host "  Container exists: tfstate" -ForegroundColor Yellow
    }
    
    # Assign storage role
    $storageId = az storage account show --name $TerraformStateAccount --resource-group $TerraformStateRG --query id -o tsv
    $storageRoleExists = az role assignment list --assignee $AppId --role "Storage Blob Data Contributor" --scope $storageId --query "[0].id" -o tsv 2>$null
    
    if (-not $storageRoleExists) {
        az role assignment create `
            --assignee $AppId `
            --role "Storage Blob Data Contributor" `
            --scope $storageId | Out-Null
        Write-Host "  Assigned Storage Blob Data Contributor role" -ForegroundColor Green
    } else {
        Write-Host "  Storage role already assigned" -ForegroundColor Yellow
    }
} else {
    Write-Host "[5/5] Skipping Terraform State Storage setup" -ForegroundColor Yellow
}

# ============================================
# Summary
# ============================================
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Add these variables to GitHub Repository Settings:" -ForegroundColor Yellow
Write-Host "(Settings -> Secrets and variables -> Actions -> Variables)" -ForegroundColor Gray
Write-Host ""
Write-Host "  AZURE_CLIENT_ID        = $AppId" -ForegroundColor White
Write-Host "  AZURE_TENANT_ID        = $TenantId" -ForegroundColor White
Write-Host "  AZURE_SUBSCRIPTION_ID  = $SubscriptionId" -ForegroundColor White

if ($SetupTerraformState) {
    Write-Host "  TFSTATE_RG             = $TerraformStateRG" -ForegroundColor White
    Write-Host "  TFSTATE_ACCOUNT        = $TerraformStateAccount" -ForegroundColor White
    Write-Host "  TFSTATE_CONTAINER      = tfstate" -ForegroundColor White
}

Write-Host ""
Write-Host "Additional variables to configure:" -ForegroundColor Yellow
Write-Host "  ACR_NAME               = (your Azure Container Registry name)" -ForegroundColor Gray
Write-Host "  PROJECT_NAME           = OpenAIWorkshop" -ForegroundColor Gray
Write-Host "  ITERATION              = 002" -ForegroundColor Gray
Write-Host "  AZ_REGION              = eastus2" -ForegroundColor Gray
Write-Host ""

# Output JSON for easy copying
$output = @{
    AZURE_CLIENT_ID = $AppId
    AZURE_TENANT_ID = $TenantId
    AZURE_SUBSCRIPTION_ID = $SubscriptionId
    TFSTATE_RG = $TerraformStateRG
    TFSTATE_ACCOUNT = $TerraformStateAccount
    TFSTATE_CONTAINER = "tfstate"
}

$outputFile = Join-Path $PSScriptRoot "github-variables.json"
$output | ConvertTo-Json | Out-File $outputFile -Encoding utf8
Write-Host "Variables saved to: $outputFile" -ForegroundColor Cyan
