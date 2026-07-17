# Start Ushirika backend (prefers 8001 if 8000 is stuck on stale process)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\Backend

$port = 8001
try {
  $c = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
  if (-not $c) { $port = 8000 }
} catch { }

Write-Host "Starting API on http://127.0.0.1:$port ..."
$env:PYTHONPATH = "."
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $port --reload
