<#
.SYNOPSIS
    Stops all PrivateVault services started by start_all.ps1.
.DESCRIPTION
    This script finds and kills Python processes that correspond to the PrivateVault services.
#>

Write-Host "Stopping all PrivateVault services..." -ForegroundColor Red

# Find and stop uvicorn processes (Port 8000, 8001, 8002)
# We match processes that contain "uvicorn" and "800" in their command line.
$UvicornProcesses = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'python3.exe'" | Where-Object { $_.CommandLine -like "*uvicorn*" -and ($_.CommandLine -like "*8000*" -or $_.CommandLine -like "*8001*" -or $_.CommandLine -like "*8002*") }

if ($UvicornProcesses) {
    Write-Host "Stopping $($UvicornProcesses.Count) uvicorn servers..." -ForegroundColor Yellow
    foreach ($Proc in $UvicornProcesses) {
        Stop-Process -Id $Proc.ProcessId -Force
    }
}

# Find and stop http.server (Port 8003)
$HttpProcesses = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'python3.exe'" | Where-Object { $_.CommandLine -like "*http.server*" -and $_.CommandLine -like "*8003*" }

if ($HttpProcesses) {
    Write-Host "Stopping $($HttpProcesses.Count) demo frontend server..." -ForegroundColor Yellow
    foreach ($Proc in $HttpProcesses) {
        Stop-Process -Id $Proc.ProcessId -Force
    }
}

Write-Host "All services stopped." -ForegroundColor Red
