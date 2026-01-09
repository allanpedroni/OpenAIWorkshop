#!/usr/bin/env pwsh
<#
Ensures Entra ID applications exist for the OpenAI Workshop deployment. If the
Azure Developer CLI environment already has AAD settings, the script leaves them
untouched. Otherwise it provisions:
  * Backend API app registration exposing user_impersonation scope
  * Frontend public client (SPA) app registration configured to request that scope
The resulting identifiers are persisted into the azd environment so Bicep can
consume them during provisioning.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-AzdEnvValue {
    param(
        [Parameter(Mandatory=$true)][string]$Name
    )
    try {
        $raw = azd env get-value $Name 2>$null
        if (-not $raw) {
            return ''
        }
        $value = $raw.Trim()
        if ($value -match '^ERROR:') {
            return ''
        }
        return $value
    } catch {
        return ''
    }
}

function Set-AzdEnvValue {
    param(
        [Parameter(Mandatory=$true)][string]$Name,
        [Parameter(Mandatory=$true)][string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }
    azd env set $Name $Value | Out-Null
}

function Ensure-AppApiScope {
    param(
        [Parameter(Mandatory=$true)][string]$AppId,
        [Parameter(Mandatory=$true)][pscustomobject]$ScopeDefinition
    )

    $apiJson = az ad app show --id $AppId --query api 2>$null
    if ($apiJson) {
        $apiObject = $apiJson | ConvertFrom-Json
    }
    if (-not $apiObject) {
        $apiObject = [pscustomobject]@{}
    }

    $existingScopes = @()
    if ($apiObject.oauth2PermissionScopes) {
        $existingScopes = @($apiObject.oauth2PermissionScopes)
    }

    $matchingScope = $existingScopes | Where-Object { $_.value -eq $ScopeDefinition.value }
    if ($matchingScope) {
        return $matchingScope[0].id
    }

    $updatedScopes = $existingScopes + $ScopeDefinition
    $apiObject | Add-Member -NotePropertyName oauth2PermissionScopes -NotePropertyValue $updatedScopes -Force

    $apiFile = New-TemporaryFile
    $apiObject | ConvertTo-Json -Depth 16 -Compress | Set-Content -Path $apiFile -Encoding utf8
    az ad app update --id $AppId --set "api=@$apiFile" | Out-Null
    Remove-Item $apiFile -Force

    return $ScopeDefinition.id
}

function Set-AppSpaRedirectUris {
    param(
        [Parameter(Mandatory=$true)][string]$AppId,
        [Parameter(Mandatory=$true)][array]$RedirectUris
    )

    $spaJson = az ad app show --id $AppId --query spa 2>$null
    if ($spaJson) {
        $spaObject = $spaJson | ConvertFrom-Json
    }
    if (-not $spaObject) {
        $spaObject = [pscustomobject]@{}
    }

    $spaObject | Add-Member -NotePropertyName redirectUris -NotePropertyValue $RedirectUris -Force

    $spaFile = New-TemporaryFile
    $spaObject | ConvertTo-Json -Depth 4 -Compress | Set-Content -Path $spaFile -Encoding utf8
    az ad app update --id $AppId --set "spa=@$spaFile" | Out-Null
    Remove-Item $spaFile -Force
}

function Get-ContainerAppRedirectUris {
    $resourceGroup = Get-AzdEnvValue 'AZURE_RESOURCE_GROUP'
    if (-not $resourceGroup) {
        return @()
    }

    try {
        $appsJson = az containerapp list --resource-group $resourceGroup 2>$null
        if (-not $appsJson) {
            return @()
        }

        $apps = $appsJson | ConvertFrom-Json
        if (-not $apps) {
            return @()
        }

        if ($apps -isnot [System.Collections.IEnumerable]) {
            $apps = @($apps)
        }

        $uris = @()
        foreach ($app in $apps) {
            if (-not $app.tags) {
                continue
            }
            $serviceName = $app.tags.'azd-service-name'
            if ($serviceName -ne 'app') {
                continue
            }
            $fqdn = $app.properties.configuration.ingress.fqdn
            if ($fqdn) {
                $uri = "https://$fqdn"
                if ($uris -notcontains $uri) {
                    $uris += $uri
                }
            }
        }

        return $uris
    } catch {
        return @()
    }
}


$environmentName = Get-AzdEnvValue 'AZURE_ENV_NAME'
if (-not $environmentName) {
    $environmentName = 'openaiworkshop'
}

$tenantId = Get-AzdEnvValue 'AAD_TENANT_ID'
if (-not $tenantId) {
    $tenantId = az account show --query tenantId -o tsv
    Set-AzdEnvValue 'AAD_TENANT_ID' $tenantId
}

if (-not (Get-AzdEnvValue 'AAD_ALLOWED_DOMAIN')) {
    Set-AzdEnvValue 'AAD_ALLOWED_DOMAIN' 'microsoft.com'
}

if (-not (Get-AzdEnvValue 'DISABLE_AUTH')) {
    Set-AzdEnvValue 'DISABLE_AUTH' 'false'
}

function Ensure-ApiApplication {
    param(
        [string]$ExistingAppId
    )

    $appId = $ExistingAppId
    $identifierUri = ''
    $scopeId = ''

    if (-not $appId) {
        $displayName = "openai-workshop-api-$environmentName"
        Write-Host "Creating Entra ID application '$displayName' for API"
        $app = az ad app create --display-name $displayName --sign-in-audience AzureADMyOrg --enable-access-token-issuance true --enable-id-token-issuance false | ConvertFrom-Json
        $appId = $app.appId
        Set-AzdEnvValue 'AAD_API_APP_ID' $appId
    } else {
        $app = az ad app show --id $appId | ConvertFrom-Json
    }

    $identifierUri = "api://$appId"
    az ad app update --id $appId --identifier-uris $identifierUri | Out-Null
    az ad app update --id $appId --requested-access-token-version 2 | Out-Null

    $scope = az ad app show --id $appId --query "api.oauth2PermissionScopes[?value=='user_impersonation'] | [0]" 2>$null
    if ($scope) {
        $scopeObj = $scope | ConvertFrom-Json
        $scopeId = $scopeObj.id
    } else {
        $scopeId = (New-Guid).Guid
        $scopePayload = [pscustomobject]@{
            adminConsentDescription = 'Access OpenAI Workshop API'
            adminConsentDisplayName = 'Access OpenAI Workshop API'
            id = $scopeId
            isEnabled = $true
            type = 'User'
            userConsentDescription = 'Allow the application to access the OpenAI Workshop API on your behalf.'
            userConsentDisplayName = 'Access OpenAI Workshop API'
            value = 'user_impersonation'
        }
        $scopeId = Ensure-AppApiScope -AppId $appId -ScopeDefinition $scopePayload
    }

    Set-AzdEnvValue 'AAD_API_AUDIENCE' $identifierUri
    Set-AzdEnvValue 'AAD_API_SCOPE' "$identifierUri/user_impersonation"
    Set-AzdEnvValue 'AAD_API_SCOPE_ID' $scopeId

    return @{ AppId = $appId; ScopeId = $scopeId }
}

function Ensure-FrontendApplication {
    param(
        [string]$ExistingClientId,
        [string]$ApiAppId,
        [string]$ScopeId
    )

    $clientId = $ExistingClientId

    if (-not $clientId) {
        $displayName = "openai-workshop-client-$environmentName"
        Write-Host "Creating Entra ID application '$displayName' for frontend"
        $app = az ad app create --display-name $displayName --sign-in-audience AzureADMyOrg --enable-id-token-issuance true --enable-access-token-issuance true | ConvertFrom-Json
        $clientId = $app.appId
        Set-AzdEnvValue 'AAD_FRONTEND_CLIENT_ID' $clientId
    }

    $redirectUris = @('http://localhost:3000','https://localhost:7000')
    $deployedRedirects = @(Get-ContainerAppRedirectUris)
    if ($deployedRedirects.Length -gt 0) {
        $redirectUris = ($redirectUris + $deployedRedirects) | Sort-Object -Unique
    }
    Set-AppSpaRedirectUris -AppId $clientId -RedirectUris $redirectUris

    if ($ApiAppId -and $ScopeId) {
        try {
            az ad app permission add --id $clientId --api $ApiAppId --api-permissions "$ScopeId=Scope" | Out-Null
        } catch {
            Write-Host "Permission assignment may already exist: $($_.Exception.Message)"
        }
    }

    return $clientId
}

$apiInfo = Ensure-ApiApplication (Get-AzdEnvValue 'AAD_API_APP_ID')
Ensure-FrontendApplication (Get-AzdEnvValue 'AAD_FRONTEND_CLIENT_ID') $apiInfo.AppId $apiInfo.ScopeId | Out-Null

Write-Host 'Entra ID configuration ensured for azd environment.'
