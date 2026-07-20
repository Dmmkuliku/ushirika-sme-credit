# Start frontend Vite and auto-start backend when needed.
$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path "$PSScriptRoot\.."
$backendScript = Join-Path $repoRoot "scripts\start_backend.ps1"

function Test-PortListening($port) {
  try {
    $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return [bool]$c
  } catch {
    return $false
  }
}

$apiUp = (Test-PortListening 8000) -or (Test-PortListening 8001)
if (-not $apiUp) {
  Write-Host "Backend not running. Starting backend automatically..."
  Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$backendScript`""
  Start-Sleep -Seconds 2
}

Set-Location (Join-Path $repoRoot "Frontend")
if (-not (Test-Path "node_modules")) { npm install }
npm run dev
