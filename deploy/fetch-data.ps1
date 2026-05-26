param(
    [string]$Name = "reply_audit.json",
    [string]$HostAlias = "oracle-reddit-bot",
    [string]$RemoteRepo = "~/wise_old_man_bot",
    [string]$OutputName = ""
)

$ErrorActionPreference = "Stop"

if ([System.IO.Path]::IsPathRooted($Name) -or $Name -match '(^|[\\/])\.\.([\\/]|$)') {
    throw "Name must be a path relative to the remote data directory."
}

$dataDir = Join-Path $PSScriptRoot "..\data"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

if (-not $OutputName) {
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($Name)
    $extension = [System.IO.Path]::GetExtension($Name)
    $OutputName = "$baseName.from-server$extension"
}

$remotePath = "${HostAlias}:${RemoteRepo}/data/${Name}"
$localPath = Join-Path $dataDir $OutputName

scp $remotePath $localPath
Write-Host "Fetched $remotePath -> $localPath"
