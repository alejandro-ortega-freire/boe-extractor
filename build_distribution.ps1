$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Get-Command python.exe -All |
    Where-Object { $_.Source -notlike "*\WindowsApps\*" } |
    Select-Object -First 1 -ExpandProperty Source

if (-not $python) {
    throw "No se encontro un python.exe real para crear la distribucion."
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name BOEExtractor `
    --exclude-module numpy `
    --exclude-module PIL `
    --exclude-module matplotlib `
    --exclude-module pandas `
    --exclude-module scipy `
    --exclude-module tkinter `
    (Join-Path $root "main.py")

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no pudo crear la distribucion."
}

$appDir = Join-Path $root "dist\BOEExtractor"
New-Item -ItemType Directory -Force -Path (Join-Path $appDir "input"), (Join-Path $appDir "output") | Out-Null
Copy-Item -Path (Join-Path $root "assets") -Destination (Join-Path $appDir "assets") -Recurse -Force
attrib +h (Join-Path $appDir "assets")

Write-Host "Distribucion creada en: $appDir"
