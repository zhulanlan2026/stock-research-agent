param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$FinancialDataPath = "./data/financial-facts.jsonl"
)

$ErrorActionPreference = "Stop"

Write-Host "== Python =="
python --version

Write-Host "== XTQuant =="
python -c "import xtquant; print('xtquant import ok')"

Write-Host "== Backend health =="
try {
    $health = Invoke-RestMethod -Uri "$BackendUrl/health/ready" -TimeoutSec 5
    $health | ConvertTo-Json -Depth 4
} catch {
    Write-Error "Backend /health/ready is not reachable: $_"
}

Write-Host "== Financial data file =="
if (Test-Path $FinancialDataPath) {
    $count = (Get-Content $FinancialDataPath | Where-Object { $_.Trim() }).Count
    Write-Host "$FinancialDataPath exists, $count lines"
} else {
    Write-Error "$FinancialDataPath does not exist"
}

Write-Host "== Collector config =="
Get-ChildItem Env:COLLECTOR_* | Sort-Object Name

Write-Host "readiness check completed"
