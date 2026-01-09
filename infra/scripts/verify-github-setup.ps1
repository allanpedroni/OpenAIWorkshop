# Verify GitHub Actions Setup Script
# Checks that all required Azure resources and permissions are configured correctly

param(
    [Parameter(Mandatory=$false)]
    [string]$AppId = "",
    
    [Parameter(Mandatory=$false)]
    [string]$TerraformStateRG = "rg-tfstate",
    
    [Parameter(Mandatory=$false)]
    [string]$TerraformStateAccount = "sttfstateoaiworkshop"
)

$ErrorActionPreference = 'Continue'

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "GitHub Actions Setup Verification" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# Get current context
$SubscriptionId = az account show --query id -o tsv
$TenantId = az account show --query tenantId -o tsv

Write-Host "Current Azure Context:" -ForegroundColor Yellow
Write-Host "  Subscription: $SubscriptionId" -ForegroundColor Gray
Write-Host "  Tenant:       $TenantId" -ForegroundColor Gray
Write-Host ""

# ============================================
# Check App Registration
# ============================================
Write-Host "[1/5] Checking App Registration..." -ForegroundColor Green

if (-not $AppId) {
    $AppId = az ad app list --display-name "GitHub-Actions-OpenAIWorkshop" --query "[0].appId" -o tsv 2>$null
}

if ($AppId) {
    Write-Host "  ✅ App Registration found: $AppId" -ForegroundColor Green
    
    # Check service principal
    $spId = az ad sp show --id $AppId --query id -o tsv 2>$null
    if ($spId) {
        Write-Host "  ✅ Service Principal exists" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Service Principal NOT found" -ForegroundColor Red
        $allPassed = $false
    }
} else {
    Write-Host "  ❌ App Registration NOT found" -ForegroundColor Red
    $allPassed = $false
}

# ============================================
# Check Federated Credentials
# ============================================
Write-Host "`n[2/5] Checking Federated Credentials..." -ForegroundColor Green

if ($AppId) {
    $appObjectId = az ad app show --id $AppId --query id -o tsv 2>$null
    $creds = az ad app federated-credential list --id $appObjectId --query "[].name" -o tsv 2>$null
    
    if ($creds) {
        $credList = $creds -split "`n"
        foreach ($cred in $credList) {
            Write-Host "  ✅ $cred" -ForegroundColor Green
        }
    } else {
        Write-Host "  ❌ No federated credentials found" -ForegroundColor Red
        $allPassed = $false
    }
} else {
    Write-Host "  ⚠️  Skipped (no App Registration)" -ForegroundColor Yellow
}

# ============================================
# Check Role Assignments
# ============================================
Write-Host "`n[3/5] Checking Role Assignments..." -ForegroundColor Green

if ($AppId) {
    $roles = az role assignment list --assignee $AppId --query "[].roleDefinitionName" -o tsv 2>$null
    
    $requiredRoles = @("Contributor", "User Access Administrator")
    foreach ($role in $requiredRoles) {
        if ($roles -match $role) {
            Write-Host "  ✅ $role" -ForegroundColor Green
        } else {
            Write-Host "  ❌ $role - NOT assigned" -ForegroundColor Red
            $allPassed = $false
        }
    }
} else {
    Write-Host "  ⚠️  Skipped (no App Registration)" -ForegroundColor Yellow
}

# ============================================
# Check Terraform State Storage
# ============================================
Write-Host "`n[4/5] Checking Terraform State Storage..." -ForegroundColor Green

# Check resource group
$rgExists = az group exists --name $TerraformStateRG 2>$null
if ($rgExists -eq "true") {
    Write-Host "  ✅ Resource Group: $TerraformStateRG" -ForegroundColor Green
} else {
    Write-Host "  ❌ Resource Group NOT found: $TerraformStateRG" -ForegroundColor Red
    $allPassed = $false
}

# Check storage account
$storageExists = az storage account show --name $TerraformStateAccount --resource-group $TerraformStateRG --query name -o tsv 2>$null
if ($storageExists) {
    Write-Host "  ✅ Storage Account: $TerraformStateAccount" -ForegroundColor Green
    
    # Check container
    $containerExists = az storage container exists --name tfstate --account-name $TerraformStateAccount --auth-mode login --query exists -o tsv 2>$null
    if ($containerExists -eq "true") {
        Write-Host "  ✅ Container: tfstate" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Container 'tfstate' NOT found" -ForegroundColor Red
        $allPassed = $false
    }
    
    # Check storage role
    if ($AppId) {
        $storageId = az storage account show --name $TerraformStateAccount --resource-group $TerraformStateRG --query id -o tsv 2>$null
        $storageRole = az role assignment list --assignee $AppId --role "Storage Blob Data Contributor" --scope $storageId --query "[0].id" -o tsv 2>$null
        if ($storageRole) {
            Write-Host "  ✅ Storage Blob Data Contributor role assigned" -ForegroundColor Green
        } else {
            Write-Host "  ❌ Storage Blob Data Contributor role NOT assigned" -ForegroundColor Red
            $allPassed = $false
        }
    }
} else {
    Write-Host "  ❌ Storage Account NOT found: $TerraformStateAccount" -ForegroundColor Red
    $allPassed = $false
}

# ============================================
# Check ACR (if exists)
# ============================================
Write-Host "`n[5/5] Checking Azure Container Registry..." -ForegroundColor Green

$acrList = az acr list --query "[].name" -o tsv 2>$null
if ($acrList) {
    $acrNames = $acrList -split "`n"
    foreach ($acr in $acrNames) {
        if ($acr -match "openai|workshop") {
            Write-Host "  ✅ ACR found: $acr" -ForegroundColor Green
            
            # Check AcrPush role
            if ($AppId) {
                $acrId = az acr show --name $acr --query id -o tsv 2>$null
                $acrRole = az role assignment list --assignee $AppId --scope $acrId --query "[?contains(roleDefinitionName,'Acr')].roleDefinitionName" -o tsv 2>$null
                if ($acrRole) {
                    Write-Host "    ✅ ACR role: $acrRole" -ForegroundColor Green
                } else {
                    Write-Host "    ⚠️  No explicit ACR role (may use Contributor)" -ForegroundColor Yellow
                }
            }
        }
    }
} else {
    Write-Host "  ⚠️  No ACR found (will be created by Terraform)" -ForegroundColor Yellow
}

# ============================================
# Summary
# ============================================
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan

if ($allPassed) {
    Write-Host "All checks passed! ✅" -ForegroundColor Green
} else {
    Write-Host "Some checks failed! ❌" -ForegroundColor Red
    Write-Host ""
    Write-Host "Run setup-github-oidc.ps1 to fix issues:" -ForegroundColor Yellow
    Write-Host "  .\setup-github-oidc.ps1 -GitHubOrg YOUR_ORG -GitHubRepo YOUR_REPO" -ForegroundColor Gray
}

Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Output GitHub variables
if ($AppId) {
    Write-Host "GitHub Repository Variables to configure:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  AZURE_CLIENT_ID       = $AppId" -ForegroundColor White
    Write-Host "  AZURE_TENANT_ID       = $TenantId" -ForegroundColor White
    Write-Host "  AZURE_SUBSCRIPTION_ID = $SubscriptionId" -ForegroundColor White
    Write-Host "  TFSTATE_RG            = $TerraformStateRG" -ForegroundColor White
    Write-Host "  TFSTATE_ACCOUNT       = $TerraformStateAccount" -ForegroundColor White
    Write-Host "  TFSTATE_CONTAINER     = tfstate" -ForegroundColor White
    Write-Host ""
}
