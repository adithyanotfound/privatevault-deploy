<#
.SYNOPSIS
    Starts all PrivateVault services in new Terminal windows.
.DESCRIPTION
    This script activates the virtual environment and starts PrivateVault.ai, BotBook.dev, LORK, and Demo Frontend on their respective ports.
#>

$ScriptPath = $PSScriptRoot
Set-Location $ScriptPath

# Check for .venv and create if missing
if (-Not (Test-Path "$ScriptPath\.venv")) {
    Write-Host ".venv not found. Creating virtual environment and installing dependencies..." -ForegroundColor Blue
    $Python = if (Get-Command "python3" -ErrorAction SilentlyContinue) { "python3" } else { "python" }
    & $Python -m venv .venv
    
    # Activate and install
    & ".\.venv\Scripts\Activate.ps1"
    python -m pip install --upgrade pip
    
    Write-Host "Installing LORK..." -ForegroundColor Blue
    pip install -e .\LORK
    
    Write-Host "Installing BotBook..." -ForegroundColor Blue
    pip install -e .\botbook.dev
    
    Write-Host "Installing PrivateVault requirements..." -ForegroundColor Blue
    pip install -r .\PrivateVault.ai\requirements.txt
    
    Write-Host "Installing shared dependencies..." -ForegroundColor Blue
    pip install pyyaml openai google-genai python-dotenv
    
    Write-Host "Setup complete!`n" -ForegroundColor Green
}

# Function to start a service in a new window
function Start-Service-Window {
    param (
        [string]$Name,
        [string]$Directory,
        [string]$Command
    )

    Write-Host "[+] Starting $Name..." -ForegroundColor Green
    
    # PowerShell 7 (pwsh) or PowerShell Desktop (powershell)
    $Shell = if (Get-Command "pwsh" -ErrorAction SilentlyContinue) { "pwsh.exe" } else { "powershell.exe" }

    Start-Process $Shell -ArgumentList "-NoExit", "-Command", "cd '$ScriptPath\$Directory'; source ../.venv/bin/activate; $Command" -WindowStyle Normal
}

# Start all services
Start-Service-Window "PrivateVault.ai (Port 8000)" "PrivateVault.ai" "python -m uvicorn main:app --reload --port 8000"
Start-Service-Window "BotBook.dev (Port 8001)" "botbook.dev" "python -m uvicorn main:app --reload --port 8001"
Start-Service-Window "LORK Control Plane (Port 8002)" "LORK" "python -m uvicorn lork.api_server:app --reload --port 8002"
Start-Service-Window "Demo Frontend (Port 8003)" "demo-frontend" "python -m http.server 8003"

Write-Host "`n--------------------------------------------------------" -ForegroundColor Cyan
Write-Host "All services started in separate windows." -ForegroundColor Green
Write-Host "PrivateVault:  http://localhost:8000" -ForegroundColor Cyan
Write-Host "BotBook:       http://localhost:8001" -ForegroundColor Cyan
Write-Host "LORK:          http://localhost:8002" -ForegroundColor Cyan
Write-Host "Demo Frontend: http://localhost:8003" -ForegroundColor Cyan
Write-Host "--------------------------------------------------------" -ForegroundColor Cyan
