# ═══ PrivateVault Demo — Start All Servers ═══
# Run this script to start all 3 backend services and the frontend

Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  PrivateVault.ai — Demo Platform Startup" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$ROOT = Split-Path $MyInvocation.MyCommand.Path

Write-Host "[1/4] Starting PrivateVault.ai on port 8000..." -ForegroundColor Yellow
$pv = Start-Process -NoNewWindow -PassThru -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--port", "8000", "--host", "0.0.0.0" -WorkingDirectory "$ROOT\PrivateVault.ai"

Write-Host "[2/4] Starting BotBook.dev on port 8001..." -ForegroundColor Yellow
$bb = Start-Process -NoNewWindow -PassThru -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--port", "8001", "--host", "0.0.0.0" -WorkingDirectory "$ROOT\botbook.dev"

Write-Host "[3/4] Starting LORK on port 8002..." -ForegroundColor Yellow
$lk = Start-Process -NoNewWindow -PassThru -FilePath "python" -ArgumentList "-m", "uvicorn", "lork.api_server:app", "--reload", "--port", "8002", "--host", "0.0.0.0" -WorkingDirectory "$ROOT\LORK"

Write-Host "[4/4] Starting Frontend on port 3000..." -ForegroundColor Yellow
$fe = Start-Process -NoNewWindow -PassThru -FilePath "python" -ArgumentList "-m", "http.server", "3000" -WorkingDirectory "$ROOT\demo-frontend"

Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "" -ForegroundColor Green
Write-Host "  PrivateVault.ai:  http://localhost:8000" -ForegroundColor White
Write-Host "  BotBook.dev:      http://localhost:8001" -ForegroundColor White
Write-Host "  LORK:             http://localhost:8002" -ForegroundColor White
Write-Host "  Dashboard:        http://localhost:3000" -ForegroundColor Cyan
Write-Host "  Swagger (PVault): http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Green

try {
    Wait-Process -Id $pv.Id, $bb.Id, $lk.Id, $fe.Id
} finally {
    Stop-Process $pv -ErrorAction SilentlyContinue
    Stop-Process $bb -ErrorAction SilentlyContinue
    Stop-Process $lk -ErrorAction SilentlyContinue
    Stop-Process $fe -ErrorAction SilentlyContinue
}
