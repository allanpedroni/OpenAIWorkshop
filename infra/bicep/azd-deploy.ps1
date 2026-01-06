#!/usr/bin/env pwsh
# Azure Developer CLI (azd) Deployment Script for OpenAI Workshop
# This script properly handles the two-phase deployment:
# Phase 1: Provision infrastructure (without Container Apps)
# Phase 2: Build, push images, then deploy Container Apps

param(
    [Parameter(Mandatory=$false)]
    [switch]$ProvisionOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$DeployOnly,
    
    [Parameter(Mandatory=$false)]
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Azure OpenAI Workshop - azd Deployment" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

# Check if azd is installed
if (-not (Get-Command azd -ErrorAction SilentlyContinue)) {
    Write-Error "Azure Developer CLI (azd) is not installed. Please install it first: https://aka.ms/azd-install"
    exit 1
}

# Get current environment
$envName = azd env get-values | Select-String "AZURE_ENV_NAME" | ForEach-Object { ($_ -replace '.*=', '').Trim('"') }

if (-not $envName) {
    Write-Host "`nNo azd environment found. Please run 'azd init' first." -ForegroundColor Yellow
    Write-Host "Or set up a new environment:" -ForegroundColor Yellow
    Write-Host "  azd env new <environment-name>" -ForegroundColor Cyan
    Write-Host "  azd env set AZURE_LOCATION eastus2" -ForegroundColor Cyan
    exit 1
}

Write-Host "`nEnvironment: $envName" -ForegroundColor Yellow

if ($Clean) {
    Write-Host "`n[CLEAN] Removing all resources..." -ForegroundColor Red
    $confirm = Read-Host "This will delete all resources in environment '$envName'. Are you sure? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Host "Clean cancelled." -ForegroundColor Yellow
        exit 0
    }
    azd down --force --purge
    exit 0
}

# Phase 1: Provision Infrastructure
if (-not $DeployOnly) {
    Write-Host "`n[PHASE 1] Provisioning Azure Infrastructure..." -ForegroundColor Green
    Write-Host "This will create: Resource Group, OpenAI, Cosmos DB, ACR, Log Analytics, Container Apps Environment" -ForegroundColor Gray
    
    azd provision
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Infrastructure provisioning failed!"
        exit 1
    }
    
    Write-Host "`nInfrastructure provisioned successfully!" -ForegroundColor Green
    
    if ($ProvisionOnly) {
        Write-Host "`n--ProvisionOnly specified. Stopping here." -ForegroundColor Yellow
        Write-Host "To deploy containers, run: azd deploy" -ForegroundColor Cyan
        exit 0
    }
}

# Phase 2: Build, Push, and Deploy Container Apps
Write-Host "`n[PHASE 2] Building and deploying containers..." -ForegroundColor Green

# Step 2.1: Package services (build Docker images)
Write-Host "`n  [2.1] Packaging services..." -ForegroundColor Cyan
azd package

if ($LASTEXITCODE -ne 0) {
    Write-Error "Service packaging failed!"
    exit 1
}

# Step 2.2: Get image names from environment
$mcpImageName = azd env get-values | Select-String "SERVICE_MCP_IMAGE_NAME" | ForEach-Object { 
    ($_ -replace '.*=', '').Trim('"') 
}
$appImageName = azd env get-values | Select-String "SERVICE_APP_IMAGE_NAME" | ForEach-Object { 
    ($_ -replace '.*=', '').Trim('"') 
}

Write-Host "`n  MCP Image: $mcpImageName" -ForegroundColor Gray
Write-Host "  App Image: $appImageName" -ForegroundColor Gray

# Step 2.3: Get ACR credentials and login
$acrName = azd env get-values | Select-String "AZURE_CONTAINER_REGISTRY_NAME" | ForEach-Object { 
    ($_ -replace '.*=', '').Trim('"') 
}

Write-Host "`n  [2.2] Logging into Azure Container Registry..." -ForegroundColor Cyan
az acr login --name $acrName

if ($LASTEXITCODE -ne 0) {
    Write-Error "ACR login failed!"
    exit 1
}

# Step 2.4: Push MCP image to ACR
Write-Host "`n  [2.3] Pushing MCP service image to ACR..." -ForegroundColor Cyan

# Get local MCP image name (without registry prefix)
$localMcpImage = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String "openai-workshop/mcp-" | Select-Object -First 1 | ForEach-Object { $_.ToString() }

if ($localMcpImage) {
    Write-Host "  Tagging: $localMcpImage -> $mcpImageName" -ForegroundColor Gray
    docker tag $localMcpImage $mcpImageName
    
    Write-Host "  Pushing: $mcpImageName" -ForegroundColor Gray
    docker push $mcpImageName
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push MCP image!"
        exit 1
    }
} else {
    Write-Warning "No MCP image found locally. Skipping MCP push."
}

# Step 2.5: Push App image to ACR
Write-Host "`n  [2.4] Pushing application image to ACR..." -ForegroundColor Cyan

$localAppImage = docker images --format "{{.Repository}}:{{.Tag}}" | Select-String "openai-workshop/app-" | Select-Object -First 1 | ForEach-Object { $_.ToString() }

if ($localAppImage) {
    Write-Host "  Tagging: $localAppImage -> $appImageName" -ForegroundColor Gray
    docker tag $localAppImage $appImageName
    
    Write-Host "  Pushing: $appImageName" -ForegroundColor Gray
    docker push $appImageName
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to push application image!"
        exit 1
    }
} else {
    Write-Warning "No application image found locally. Skipping app push."
}

# Step 2.6: Ensure image names are set in environment
Write-Host "`n  [2.5] Setting image names in environment..." -ForegroundColor Cyan
azd env set SERVICE_MCP_IMAGE_NAME $mcpImageName
azd env set SERVICE_APP_IMAGE_NAME $appImageName

# Step 2.7: Provision again to create Container Apps with images
Write-Host "`n  [2.6] Creating Container Apps with deployed images..." -ForegroundColor Cyan
azd provision

if ($LASTEXITCODE -ne 0) {
    Write-Error "Container Apps deployment failed!"
    exit 1
}

# Get final deployment URLs
Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan

$mcpUrl = azd env get-values | Select-String "MCP_SERVICE_URL" | ForEach-Object { 
    ($_ -replace '.*=', '').Trim('"') 
}
$appUrl = azd env get-values | Select-String "APPLICATION_URL" | ForEach-Object { 
    ($_ -replace '.*=', '').Trim('"') 
}
$resourceGroup = azd env get-values | Select-String "AZURE_RESOURCE_GROUP" | ForEach-Object { 
    ($_ -replace '.*=', '').Trim('"') 
}

if ($appUrl) {
    Write-Host "`nApplication URL:" -ForegroundColor Yellow
    Write-Host "  $appUrl" -ForegroundColor Cyan
}

if ($mcpUrl) {
    Write-Host "`nMCP Service URL:" -ForegroundColor Yellow
    Write-Host "  $mcpUrl" -ForegroundColor Cyan
}

Write-Host "`nResource Group:" -ForegroundColor Yellow
Write-Host "  $resourceGroup" -ForegroundColor Cyan

Write-Host "`nTo view logs:" -ForegroundColor Yellow
Write-Host "  azd monitor --overview" -ForegroundColor Cyan
Write-Host "  azd monitor --logs" -ForegroundColor Cyan

Write-Host "`nTo update deployments:" -ForegroundColor Yellow
Write-Host "  azd deploy" -ForegroundColor Cyan

Write-Host "`nTo tear down:" -ForegroundColor Yellow
Write-Host "  azd down" -ForegroundColor Cyan
