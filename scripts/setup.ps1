# First-time setup script for PrecisionOncology Portal (Windows).
# Creates .env from .env.example if it doesn't exist,
# then creates data directories.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# Create .env if missing
if (-Not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    Write-Host "Done. Edit .env to set API tokens and paths before running the pipeline."
} else {
    Write-Host ".env already exists, skipping."
}

# Create data directories
$dirs = @("data\uploads", "data\cache", "data\reference", "data\cases")
foreach ($dir in $dirs) {
    if (-Not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host ""
Write-Host "Setup complete. Next steps:"
Write-Host "  docker compose build"
Write-Host "  docker compose up -d"
