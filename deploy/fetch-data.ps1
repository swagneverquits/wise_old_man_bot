param(
    [string]$Name = "",
    [string]$HostAlias = "oracle-reddit-bot",
    [string]$RemoteRepo = "~/reddit_reply_bot",
    [string]$OutputName = "",
    [switch]$SkipExport
)

$ErrorActionPreference = "Stop"

if ($Name -and ([System.IO.Path]::IsPathRooted($Name) -or $Name -match '(^|[\\/])\.\.([\\/]|$)')) {
    throw "Name must be a path relative to the remote data directory."
}

$dataDir = Join-Path $PSScriptRoot "..\data"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

if (-not $Name) {
    $outputDir = Join-Path $dataDir "from-server"
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

    $remotePath = "${HostAlias}:${RemoteRepo}/data/*"
    scp -r $remotePath $outputDir
    Write-Host "Fetched $remotePath -> $outputDir"

    $dbPath = Join-Path $outputDir "bot_state.sqlite"
    if ((Test-Path $dbPath) -and -not $SkipExport) {
        Push-Location (Join-Path $PSScriptRoot "..")
        try {
            python -m reddit_reply_bot.maintenance export-sqlite --db $dbPath --out $outputDir
        }
        finally {
            Pop-Location
        }
    }
    exit 0
}

if (-not $OutputName) {
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($Name)
    $extension = [System.IO.Path]::GetExtension($Name)
    $OutputName = "$baseName.from-server$extension"
}

$remotePath = "${HostAlias}:${RemoteRepo}/data/${Name}"
$localPath = Join-Path $dataDir $OutputName

scp $remotePath $localPath
Write-Host "Fetched $remotePath -> $localPath"
