# Terraform State Storage Setup Script
# Creates Azure Storage Account for remote Terraform state

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "rg-tfstate",
    
    [Parameter(Mandatory=$false)]
    [string]$StorageAccount = "sttfstateoaiworkshop",
    
    [Parameter(Mandatory=$false)]
    [string]$Container = "tfstate",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus2",
    
    [Parameter(Mandatory=$false)]
    [string]$ServicePrincipalId = ""
)

$ErrorActionPreference = 'Stop'

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Terraform State Storage Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Create resource group
Write-Host "[1/4] Creating Resource Group: $ResourceGroup" -ForegroundColor Green
$rgExists = az group exists --name $ResourceGroup
if ($rgExists -eq "false") {
    az group create --name $ResourceGroup --location $Location -o table
} else {
    Write-Host "  Resource group already exists" -ForegroundColor Yellow
}

# Create storage account
Write-Host "`n[2/4] Creating Storage Account: $StorageAccount" -ForegroundColor Green
$storageExists = az storage account show --name $StorageAccount --resource-group $ResourceGroup --query name -o tsv 2>$null
if (-not $storageExists) {
    az storage account create `
        --name $StorageAccount `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku Standard_LRS `
        --allow-blob-public-access false `
        --min-tls-version TLS1_2 `
        -o table
} else {
    Write-Host "  Storage account already exists" -ForegroundColor Yellow
}

# Create blob container
Write-Host "`n[3/4] Creating Blob Container: $Container" -ForegroundColor Green
$containerExists = az storage container exists --name $Container --account-name $StorageAccount --auth-mode login --query exists -o tsv 2>$null
if ($containerExists -ne "true") {
    az storage container create `
        --name $Container `
        --account-name $StorageAccount `
        --auth-mode login `
        -o table
} else {
    Write-Host "  Container already exists" -ForegroundColor Yellow
}

# Assign role if service principal provided
if ($ServicePrincipalId) {
    Write-Host "`n[4/4] Assigning Storage Blob Data Contributor role..." -ForegroundColor Green
    $storageId = az storage account show --name $StorageAccount --resource-group $ResourceGroup --query id -o tsv
    
    $roleExists = az role assignment list `
        --assignee $ServicePrincipalId `
        --role "Storage Blob Data Contributor" `
        --scope $storageId `
        --query "[0].id" -o tsv 2>$null
    
    if (-not $roleExists) {
        az role assignment create `
            --assignee $ServicePrincipalId `
            --role "Storage Blob Data Contributor" `
            --scope $storageId `
            -o table
    } else {
        Write-Host "  Role already assigned" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[4/4] Skipping role assignment (no service principal provided)" -ForegroundColor Yellow
}

# Output summary
Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Terraform Backend Configuration:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  terraform {" -ForegroundColor Gray
Write-Host "    backend `"azurerm`" {" -ForegroundColor Gray
Write-Host "      resource_group_name  = `"$ResourceGroup`"" -ForegroundColor White
Write-Host "      storage_account_name = `"$StorageAccount`"" -ForegroundColor White
Write-Host "      container_name       = `"$Container`"" -ForegroundColor White
Write-Host "      key                  = `"terraform.tfstate`"" -ForegroundColor White
Write-Host "      use_oidc             = true" -ForegroundColor White
Write-Host "      use_azuread_auth     = true" -ForegroundColor White
Write-Host "    }" -ForegroundColor Gray
Write-Host "  }" -ForegroundColor Gray
Write-Host ""
Write-Host "GitHub Variables:" -ForegroundColor Yellow
Write-Host "  TFSTATE_RG        = $ResourceGroup" -ForegroundColor White
Write-Host "  TFSTATE_ACCOUNT   = $StorageAccount" -ForegroundColor White
Write-Host "  TFSTATE_CONTAINER = $Container" -ForegroundColor White
Write-Host ""

# For local use with deploy.ps1
Write-Host "For local deployment with remote state:" -ForegroundColor Yellow
Write-Host '  $env:TFSTATE_RG = "' + $ResourceGroup + '"' -ForegroundColor Gray
Write-Host '  $env:TFSTATE_ACCOUNT = "' + $StorageAccount + '"' -ForegroundColor Gray
Write-Host '  $env:TFSTATE_CONTAINER = "' + $Container + '"' -ForegroundColor Gray
Write-Host '  $env:TFSTATE_KEY = "myproject.tfstate"' -ForegroundColor Gray
Write-Host '  ./deploy.ps1 -RemoteBackend' -ForegroundColor Gray
