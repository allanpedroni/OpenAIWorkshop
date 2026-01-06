#!/usr/bin/env pwsh
<#!
Wrapper executed by azd preprovision hooks to ensure auth apps and local developer
Cosmos RBAC prerequisites are configured.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptRoot = Split-Path -Parent $PSCommandPath

& pwsh -File (Join-Path $scriptRoot 'setup-aad.ps1')
& pwsh -File (Join-Path $scriptRoot 'setup-local-developer.ps1')
