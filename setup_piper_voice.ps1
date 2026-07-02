<#
.SYNOPSIS
    Downloads and configures the Piper TTS voice model (en_US-amy-medium)
    into backend/voices/, matching PIPER_VOICE_MODEL_PATH / PIPER_VOICE_CONFIG_PATH
    in backend/.env and the bind mount in docker-compose.yml
    (./backend/voices:/app/voices).

.NOTES
    Run from the project root (the directory containing docker-compose.yml):
        powershell -ExecutionPolicy Bypass -File .\setup_piper_voice.ps1

    Safe to re-run: skips any file that already exists and passes a size check.
#>

$ErrorActionPreference = "Stop"

$VoicesDir   = "backend\voices"
$BaseUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium"
$ModelFile = "en_US-ryan-medium.onnx"
$ConfigFile = "en_US-ryan-medium.onnx.json"
$MinModelBytes = 10000000   # medium voice models are tens of MB; guards against truncated downloads

if (-not (Test-Path "docker-compose.yml")) {
    Write-Error "docker-compose.yml not found in current directory. Run this script from the project root."
    exit 1
}

if (-not (Test-Path $VoicesDir)) {
    New-Item -ItemType Directory -Path $VoicesDir -Force | Out-Null
}

function Get-IfMissing {
    param(
        [string]$FileName,
        [string]$Url
    )

    $dest = Join-Path $VoicesDir $FileName

    if (Test-Path $dest) {
        Write-Host "OK: $dest already exists, skipping."
        return
    }

    $tempDest = "$dest.partial"
    Write-Host "Downloading $FileName ..."

    try {
        Invoke-WebRequest -Uri $Url -OutFile $tempDest -UseBasicParsing
    } catch {
        if (Test-Path $tempDest) { Remove-Item $tempDest -Force }
        Write-Error "Failed to download $FileName from $Url : $_"
        exit 1
    }

    Move-Item -Path $tempDest -Destination $dest -Force
    Write-Host "Saved $dest"
}

Get-IfMissing -FileName $ModelFile  -Url "$BaseUrl/$ModelFile"
Get-IfMissing -FileName $ConfigFile -Url "$BaseUrl/$ConfigFile"

$modelPath  = Join-Path $VoicesDir $ModelFile
$configPath = Join-Path $VoicesDir $ConfigFile

$modelSize = (Get-Item $modelPath).Length
if ($modelSize -lt $MinModelBytes) {
    Write-Error "$modelPath is only $modelSize bytes - looks truncated or corrupted. Delete it and re-run this script."
    exit 1
}

try {
    Get-Content $configPath -Raw | ConvertFrom-Json | Out-Null
} catch {
    Write-Warning "$configPath does not look like valid JSON. Delete it and re-run this script."
}

Write-Host ""
Write-Host "Done. Voice model files are in $VoicesDir\:"
Get-ChildItem $VoicesDir | Format-Table Name, Length

Write-Host ""
Write-Host "Next: rebuild and restart the backend so piper-tts (added to requirements.txt) is installed:"
Write-Host "  docker compose build backend"
Write-Host "  docker compose up -d"