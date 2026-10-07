# HireGuard one-time setup. Run from VS Code: Terminal > Run Task > "HireGuard: Setup"
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "`n=== Checking prerequisites ===" -ForegroundColor Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found. Install Python 3.11+ from python.org (tick 'Add to PATH'), then reopen VS Code." -ForegroundColor Red
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js not found. Install the LTS version from nodejs.org, then reopen VS Code." -ForegroundColor Red
    exit 1
}
python --version
node --version

Write-Host "`n=== Backend: virtual environment ===" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path "venv")) { python -m venv venv }
$py = "$root\backend\venv\Scripts\python.exe"

Write-Host "`n=== Backend: installing packages (takes a few minutes) ===" -ForegroundColor Cyan
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed - copy the error above and share it." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Backend: creating database ===" -ForegroundColor Cyan
& $py init_db.py
if ($LASTEXITCODE -ne 0) { Write-Host "Database setup failed - copy the error above and share it." -ForegroundColor Red; exit 1 }

Write-Host "`n=== Frontend: installing packages ===" -ForegroundColor Cyan
Set-Location "$root\frontend"
npm install
if ($LASTEXITCODE -ne 0) { Write-Host "npm install failed - copy the error above and share it." -ForegroundColor Red; exit 1 }

Set-Location $root
Write-Host "`nSetup complete. Now run: Terminal > Run Task > 'HireGuard: Start'" -ForegroundColor Green
