param(
    [string]$CollectorPath = "D:\StockProject\apps\xtquant-collector",
    [string]$FinancialSource = "\\wsl.localhost\Ubuntu\home\zhutongfen\project\stock-research-agent\apps\xtquant-collector\data\financial-facts.jsonl"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $CollectorPath)) {
    Write-Error "Collector path not found: $CollectorPath"
}

$dataDir = Join-Path $CollectorPath "data"
New-Item -ItemType Directory -Force $dataDir | Out-Null

$envFile = Join-Path $CollectorPath ".env"
$backupFile = Join-Path $CollectorPath ".env.bak"
if (Test-Path $envFile) {
    Copy-Item $envFile $backupFile -Force
}

$content = @"
COLLECTOR_APP_ENV=development
COLLECTOR_BACKEND_URL=http://localhost:8000/api/v1
COLLECTOR_INGEST_TOKEN=dev-collector-token-change-me

COLLECTOR_COLLECT_SYMBOLS=600519.SH,000001.SZ,000858.SZ
COLLECTOR_COLLECT_PERIODS=1m,1d

COLLECTOR_COLLECT_NEWS_ENABLED=true
COLLECTOR_COLLECT_NEWS_KINDS=announcement

COLLECTOR_COLLECT_FINANCIAL_ENABLED=true
COLLECTOR_FINANCIAL_DATA_PATH=./data/financial-facts.jsonl

COLLECTOR_WAL_PATH=./data/collector-local-wal.sqlite
COLLECTOR_POLL_INTERVAL_SECONDS=1.0
COLLECTOR_LOG_LEVEL=INFO
"@

Set-Content -Path $envFile -Value $content -Encoding UTF8

$financialTarget = Join-Path $dataDir "financial-facts.jsonl"
if (Test-Path $FinancialSource) {
    Copy-Item $FinancialSource $financialTarget -Force
} else {
    Write-Warning "Financial source not found: $FinancialSource"
}

Write-Host "collector .env updated: $envFile"
Write-Host "financial facts file: $financialTarget"
Write-Host "backup: $backupFile"
