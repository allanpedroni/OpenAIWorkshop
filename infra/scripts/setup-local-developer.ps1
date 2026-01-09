#!/usr/bin/env pwsh
<#!
Populates the LOCAL_DEVELOPER_OBJECT_ID environment value used during secure deployments
so Cosmos DB can grant RBAC access to the current developer account.

Usage:
  pwsh ./infra/scripts/setup-local-developer.ps1               # auto-detect signed-in user
  pwsh ./infra/scripts/setup-local-developer.ps1 -ObjectId ...  # override manually
#>

[CmdletBinding()]
param(
    [string]$ObjectId
)

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

$resolvedObjectId = $null

if (-not [string]::IsNullOrWhiteSpace($ObjectId)) {
    $resolvedObjectId = $ObjectId
} else {
    $existing = Get-AzdEnvValue 'LOCAL_DEVELOPER_OBJECT_ID'
    if (-not [string]::IsNullOrWhiteSpace($existing)) {
        Write-Host "Using existing LOCAL_DEVELOPER_OBJECT_ID: $existing"
        $resolvedObjectId = $existing
    } else {
        try {
            $signedInUserRaw = az ad signed-in-user show 2>$null
            if ($signedInUserRaw) {
                $signedInUser = $signedInUserRaw | ConvertFrom-Json
                if ($signedInUser -and $signedInUser.id) {
                    $resolvedObjectId = $signedInUser.id
                    Write-Host "Detected signed-in user object ID: $resolvedObjectId"
                }
            }
        } catch {
            Write-Warning "Unable to query signed-in user via az CLI: $($_.Exception.Message)"
        }
    }
}

if ([string]::IsNullOrWhiteSpace($resolvedObjectId)) {
    Write-Warning 'Could not determine LOCAL_DEVELOPER_OBJECT_ID. Provide the ID with -ObjectId or run `azd env set LOCAL_DEVELOPER_OBJECT_ID <objectId>` manually.'
    exit 0
}

Set-AzdEnvValue 'LOCAL_DEVELOPER_OBJECT_ID' $resolvedObjectId
Write-Host "LOCAL_DEVELOPER_OBJECT_ID has been set to: $resolvedObjectId"
