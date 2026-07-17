# Start frontend Vite (proxies /api → backend on 8001 by default)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\Frontend
if (-not (Test-Path "node_modules")) { npm install }
npm run dev
