# Azure Infrastructure Deployment Script for OpenAI Workshop
# This script builds Docker images, pushes to ACR, and deploys infrastructure

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('dev', 'staging', 'prod')]
    [string]$Environment = 'dev',
    
    [Parameter(Mandatory=$false)]
    [string]$Location = 'eastus2',
    
    [Parameter(Mandatory=$false)]
    [string]$BaseName = 'openai-workshop',
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild,
    
    [Parameter(Mandatory=$false)]
    [switch]$InfraOnly
)

$ErrorActionPreference = 'Stop'

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Azure OpenAI Workshop Deployment" -ForegroundColor Cyan
Write-Host "Environment: $Environment" -ForegroundColor Cyan
Write-Host "Location: $Location" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Variables
$ResourceGroupName = "$BaseName-$Environment-rg"
$SubscriptionId = (az account show --query id -o tsv)
$AcrName = "$BaseName$Environment" + "acr" -replace '-', ''  # ACR names can't have hyphens

Write-Host "`nUsing Subscription: $SubscriptionId" -ForegroundColor Yellow

# Step 1: Deploy Infrastructure
Write-Host "`n[1/5] Deploying Azure Infrastructure..." -ForegroundColor Green
az deployment sub create `
    --location $Location `
    --template-file ./infra/main.bicep `
    --parameters location=$Location environmentName=$Environment baseName=$BaseName `
    --name "openai-workshop-$Environment-$(Get-Date -Format 'yyyyMMdd-HHmmss')" `
    --query 'properties.outputs' -o json | Out-File -FilePath "./deployment-outputs.json"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Infrastructure deployment failed!"
    exit 1
}

Write-Host "Infrastructure deployed successfully!" -ForegroundColor Green

# Read outputs
$outputs = Get-Content "./deployment-outputs.json" | ConvertFrom-Json
$AcrLoginServer = "$AcrName.azurecr.io"

Write-Host "`nDeployment Outputs:" -ForegroundColor Yellow
Write-Host "  Resource Group: $($outputs.resourceGroupName.value)" -ForegroundColor Gray
Write-Host "  ACR Name: $AcrName" -ForegroundColor Gray
Write-Host "  ACR Login Server: $AcrLoginServer" -ForegroundColor Gray
Write-Host "  MCP Service URL: $($outputs.mcpServiceUrl.value)" -ForegroundColor Gray
Write-Host "  Application URL: $($outputs.applicationUrl.value)" -ForegroundColor Gray

if ($InfraOnly) {
    Write-Host "`nInfra-only mode: Skipping container builds and deployments" -ForegroundColor Yellow
    exit 0
}

# Step 2: Login to ACR
Write-Host "`n[2/5] Logging into Azure Container Registry..." -ForegroundColor Green
az acr login --name $AcrName

if ($LASTEXITCODE -ne 0) {
    Write-Error "ACR login failed!"
    exit 1
}

# Step 3: Build and Push MCP Service Image
if (-not $SkipBuild) {
    Write-Host "`n[3/5] Building and pushing MCP Service image..." -ForegroundColor Green
    
    Push-Location mcp
    try {
        docker build -t "$AcrLoginServer/mcp-service:latest" -f Dockerfile .
        docker push "$AcrLoginServer/mcp-service:latest"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "MCP Service image build/push failed!"
            exit 1
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host "MCP Service image built and pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n[3/5] Skipping MCP Service build (--SkipBuild)" -ForegroundColor Yellow
}

# Step 4: Build and Push Application Image
if (-not $SkipBuild) {
    Write-Host "`n[4/5] Building and pushing Application image..." -ForegroundColor Green
    
    Push-Location agentic_ai/applications
    try {
        docker build -t "$AcrLoginServer/workshop-app:latest" -f Dockerfile .
        docker push "$AcrLoginServer/workshop-app:latest"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Application image build/push failed!"
            exit 1
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host "Application image built and pushed successfully!" -ForegroundColor Green
} else {
    Write-Host "`n[4/5] Skipping Application build (--SkipBuild)" -ForegroundColor Yellow
}

# Step 5: Restart Container Apps to pull new images
Write-Host "`n[5/5] Restarting Container Apps..." -ForegroundColor Green

$McpServiceName = "$BaseName-$Environment-mcp"
$AppName = "$BaseName-$Environment-app"

Write-Host "Restarting MCP Service: $McpServiceName" -ForegroundColor Gray
az containerapp revision restart `
    --resource-group $ResourceGroupName `
    --name $McpServiceName `
    --revision latest

Write-Host "Restarting Application: $AppName" -ForegroundColor Gray
az containerapp revision restart `
    --resource-group $ResourceGroupName `
    --name $AppName `
    --revision latest

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "`nAccess your application at:" -ForegroundColor Yellow
Write-Host "  $($outputs.applicationUrl.value)" -ForegroundColor Cyan
Write-Host "`nMCP Service URL:" -ForegroundColor Yellow
Write-Host "  $($outputs.mcpServiceUrl.value)" -ForegroundColor Cyan
Write-Host "`nResource Group:" -ForegroundColor Yellow
Write-Host "  $ResourceGroupName" -ForegroundColor Cyan
