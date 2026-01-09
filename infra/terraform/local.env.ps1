# Local environment configuration for Terraform deployment
# Source this file before running deploy.ps1 with remote backend
#
# Usage (PowerShell):
#   . .\local.env.ps1
#   .\deploy.ps1 -RemoteBackend

# Terraform Remote State Backend
$env:TFSTATE_RG = "rg-tfstate"
$env:TFSTATE_ACCOUNT = "sttfstateoaiworkshop"
$env:TFSTATE_CONTAINER = "tfstate"
$env:TFSTATE_KEY = "dev.terraform.tfstate"

# Azure Configuration (for reference - typically set via az login)
$env:ARM_SUBSCRIPTION_ID = "840b5c5c-3f4a-459a-94fc-6bad2a969f9d"
$env:ARM_TENANT_ID = "0fbe7234-45ea-498b-b7e4-1a8b2d3be4d9"

Write-Host "Environment variables set for Terraform deployment" -ForegroundColor Green
Write-Host "  TFSTATE_RG: $env:TFSTATE_RG"
Write-Host "  TFSTATE_ACCOUNT: $env:TFSTATE_ACCOUNT"
Write-Host "  TFSTATE_CONTAINER: $env:TFSTATE_CONTAINER"
