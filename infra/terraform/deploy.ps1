# Terraform Infrastructure Deployment Script for OpenAI Workshop
# This script deploys infrastructure via Terraform, builds Docker images, pushes to ACR, and updates Container Apps

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('dev', 'staging', 'prod')]
    [string]$Environment = 'dev',
    
    [Parameter(Mandatory=$false)]
    [string]$Location = 'eastus2',
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectName = 'OpenAIWorkshop',
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild,
    
    [Parameter(Mandatory=$false)]
    [switch]$InfraOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$PlanOnly,

    [Parameter(Mandatory=$false)]
    [switch]$RemoteBackend
)

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Azure OpenAI Workshop - Terraform Deployment" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "Location: $Location" -ForegroundColor Cyan

Write-Host "`n[Pre] Using existing Terraform variables to get iteration value..." -ForegroundColor Cyan
$tfvarsPath = "$PSScriptRoot\$Environment.tfvars"
if (-not (Test-Path $tfvarsPath)) {
    Write-Error "tfvars file not found: $tfvarsPath"
    exit 1
}

$Iteration = ((get-content $tfvarsPath | select-string iteration).Line -split "=")[1].Trim().Trim('"')
if ([String]::IsNullOrEmpty($Iteration)) {
    Write-Error "Iteration must be defined in tfvars!"
    exit 1
}

Write-Host "Iteration: $Iteration" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Get current Azure context
$SubscriptionId = (az account show --query id -o tsv)
$TenantId = (az account show --query tenantId -o tsv)

Write-Host "`nUsing Subscription: $SubscriptionId" -ForegroundColor Yellow
Write-Host "Using Tenant: $TenantId" -ForegroundColor Yellow

# Variables derived from Terraform naming conventions
$ResourceGroupName = "rg-$ProjectName-$Environment-$Iteration"
$McpServiceName = "ca-mcp-$Iteration"
$AppName = "ca-be-$Iteration"

Write-Host "`nResource Names:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor Gray
Write-Host "  MCP Container App: $McpServiceName" -ForegroundColor Gray
Write-Host "  Backend Container App: $AppName" -ForegroundColor Gray

# Step 1: Initialize Terraform
Write-Host "`n[1/6] Initializing Terraform..." -ForegroundColor Green
Push-Location $PSScriptRoot
try {
    # If remote backend is specified, use a remote backend. We will ensure that there is a properly configured backend in providers.
    # If the remote backend is not specified, we default with this interactive script to local state so we move the default config
    #   to a different file.
    if ($RemoteBackend) {
        if (test-path -path providers.tf.remote) {
            move-item providers.tf providers.tf.local
            move-item providers.tf.remote providers.tf
        }
        terraform init -upgrade -backend-config="resource_group_name=$env:TFSTATE_RG" -backend-config="key=$env:TFSTATE_KEY" -backend-config="storage_account_name=$env:TFSTATE_ACCOUNT" -backend-config="container_name=$env:TFSTATE_CONTAINER"
    } else {
        if (test-path -path providers.tf.local) {
            move-item providers.tf providers.tf.remote
            move-item providers.tf.local providers.tf
        }
        terraform init -upgrade
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform init failed!"
        exit 1
    }
}
finally {
    Pop-Location
}

# Step 2: Use existing tfvars file
Write-Host "`n[2/6] Using existing Terraform variables..." -ForegroundColor Green
$tfvarsPath = "$PSScriptRoot\$Environment.tfvars"
if (-not (Test-Path $tfvarsPath)) {
    Write-Error "tfvars file not found: $tfvarsPath"
    exit 1
}
Write-Host "  Using $tfvarsPath" -ForegroundColor Gray

# Step 3: Plan Terraform deployment
Write-Host "`n[3/6] Planning Terraform deployment..." -ForegroundColor Green
Push-Location $PSScriptRoot
try {
    terraform plan -var-file="$Environment.tfvars" -out=tfplan
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform plan failed!"
        exit 1
    }
}
finally {
    Pop-Location
}

if ($PlanOnly) {
    Write-Host "`nPlan-only mode: Skipping apply and container deployments" -ForegroundColor Yellow
    exit 0
}

# Step 4: Apply Terraform deployment
Write-Host "`n[4/6] Applying Terraform deployment..." -ForegroundColor Green
Push-Location $PSScriptRoot
try {
    terraform apply tfplan
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Terraform apply failed!"
        exit 1
    }
    
    # Get outputs from Terraform
    $McpUrl = terraform output -raw mcp_aca_url
    $BeUrl = terraform output -raw be_aca_url
    $AcrName = terraform output -raw container_registry_name
    $AcrLoginServer = terraform output -raw container_registry_login_server
}
finally {
    Pop-Location
}

Write-Host "Infrastructure deployed successfully!" -ForegroundColor Green
Write-Host "`nDeployment Outputs:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroupName" -ForegroundColor Gray
Write-Host "  MCP Service URL: $McpUrl" -ForegroundColor Gray
Write-Host "  Application URL: $BeUrl" -ForegroundColor Gray

if ($InfraOnly) {
    Write-Host "`nInfra-only mode: Skipping container builds and deployments" -ForegroundColor Yellow
    exit 0
}

# Step 5: Login to ACR and build/push images
Write-Host "`n[5/6] Logging into Azure Container Registry..." -ForegroundColor Green
az acr login --name $AcrName

if ($LASTEXITCODE -ne 0) {
    Write-Error "ACR login failed!"
    exit 1
}

if (-not $SkipBuild) {
    # Build and Push MCP Service Image
    Write-Host "`nBuilding and pushing MCP Service image..." -ForegroundColor Green
    
    Push-Location $PSScriptRoot/../../mcp
    try {
        docker build -t "$AcrLoginServer/mcp-service:$Environment-latest" -t "$AcrLoginServer/mcp-service:latest" -f Dockerfile .
        docker push "$AcrLoginServer/mcp-service" --all-tags
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "MCP Service image build/push failed!"
            exit 1
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host "MCP Service image built and pushed successfully!" -ForegroundColor Green
    
    # Build and Push Backend Application Image
    Write-Host "`nBuilding and pushing Backend Application image..." -ForegroundColor Green
    
    Push-Location $PSScriptRoot/../../agentic_ai
    try {
        docker build -t "$AcrLoginServer/backend-app:$Environment-latest" -t "$AcrLoginServer/backend-app:latest" -f applications/Dockerfile .
        docker push "$AcrLoginServer/backend-app" --all-tags
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Application image build/push failed!"
            exit 1
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host "Backend Application image built and pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "`nSkipping container builds (--SkipBuild)" -ForegroundColor Yellow
}

# Step 6: Update Container Apps to use new images
Write-Host "`n[6/6] Updating Container Apps with new images..." -ForegroundColor Green

$ErrorActionPreference = 'Continue'

Write-Host "Updating MCP Service: $McpServiceName" -ForegroundColor Gray
az containerapp update `
    --resource-group $ResourceGroupName `
    --name $McpServiceName `
    --image "$AcrLoginServer/mcp-service:$Environment-latest" `
    --output none 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "  MCP Service update skipped (container app may not exist yet)" -ForegroundColor Yellow
} else {
    Write-Host "  MCP Service updated successfully" -ForegroundColor Green
}

Write-Host "Updating Backend Application: $AppName" -ForegroundColor Gray
az containerapp update `
    --resource-group $ResourceGroupName `
    --name $AppName `
    --image "$AcrLoginServer/backend-app:$Environment-latest" `
    --output none 2>$null

if ($LASTEXITCODE -ne 0) {
    Write-Host "  Application update skipped (container app may not exist yet)" -ForegroundColor Yellow
} else {
    Write-Host "  Application updated successfully" -ForegroundColor Green
}

$ErrorActionPreference = 'Stop'

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "`nAccess your application at:" -ForegroundColor Yellow
Write-Host "  $BeUrl" -ForegroundColor Cyan
Write-Host "`nMCP Service URL:" -ForegroundColor Yellow
Write-Host "  $McpUrl" -ForegroundColor Cyan
Write-Host "`nResource Group:" -ForegroundColor Yellow
Write-Host "  $ResourceGroupName" -ForegroundColor Cyan
