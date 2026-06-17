# ============================================================
# SmartAttend — Windows PowerShell Seed Runner
# Run this from the repo ROOT directory:
#   .\apps\backend\scripts\run_seed_windows.ps1
# ============================================================

Write-Host "" 
Write-Host "SmartAttend — Seed Script Runner" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# 1. Make sure we are in the repo root
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
Set-Location $repoRoot
Write-Host "Repo root: $repoRoot" -ForegroundColor Gray

# 2. Set PYTHONPATH so Python can find the `app` package
$env:PYTHONPATH = Join-Path $repoRoot "apps\backend"
Write-Host "PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Gray

# 3. Load .env file if it exists (reads KEY=VALUE lines, skips comments)
$envFile = Join-Path $repoRoot ".env"
if (Test-Path $envFile) {
    Write-Host ".env file found — loading variables..." -ForegroundColor Gray
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#')) {
            $parts = $line -split '=', 2
            if ($parts.Count -eq 2) {
                $key = $parts[0].Trim()
                $val = $parts[1].Trim()
                [System.Environment]::SetEnvironmentVariable($key, $val, 'Process')
            }
        }
    }
    Write-Host ".env loaded." -ForegroundColor Green
} else {
    Write-Host "WARNING: No .env file found at $envFile" -ForegroundColor Yellow
    Write-Host "Setting minimal required env vars for local dev..." -ForegroundColor Yellow
    $env:SECRET_KEY = "dev-secret-key-change-in-production-min-32-chars"
    $env:DATABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/smartattend"
    $env:REDIS_URL = "redis://localhost:6379/0"
    $env:APP_ENV = "development"
    $env:APP_NAME = "SmartAttend"
    $env:ALGORITHM = "HS256"
    $env:ACCESS_TOKEN_EXPIRE_MINUTES = "30"
    $env:REFRESH_TOKEN_EXPIRE_DAYS = "7"
    $env:DATABASE_POOL_SIZE = "5"
    $env:DATABASE_MAX_OVERFLOW = "0"
    $env:QR_TOKEN_TTL_SECONDS = "120"
    $env:ML_SERVICE_URL = "http://localhost:8001"
    $env:FACE_SIMILARITY_THRESHOLD = "0.60"
    $env:PROXY_ANOMALY_THRESHOLD = "0.75"
    $env:STORAGE_PROVIDER = "local"
    $env:AWS_ACCESS_KEY_ID = ""
    $env:AWS_SECRET_ACCESS_KEY = ""
    $env:AWS_REGION = "ap-south-1"
    $env:S3_BUCKET_NAME = "smartattend-media"
    $env:SMS_PROVIDER = "twilio"
    $env:TWILIO_ACCOUNT_SID = ""
    $env:TWILIO_AUTH_TOKEN = ""
    $env:TWILIO_FROM_NUMBER = ""
    $env:EMAIL_FROM = "noreply@smartattend.in"
    $env:SMTP_HOST = "smtp.gmail.com"
    $env:SMTP_PORT = "587"
    $env:SMTP_USER = ""
    $env:SMTP_PASSWORD = ""
    $env:TOTP_ISSUER = "SmartAttend"
    $env:SENTRY_DSN = ""
    $env:CELERY_BROKER_URL = "redis://localhost:6379/1"
    $env:CELERY_RESULT_BACKEND = "redis://localhost:6379/2"
}

# 4. Run the seed script
$seedScript = Join-Path $repoRoot "apps\backend\scripts\seed_demo.py"
Write-Host ""
Write-Host "Running seed script: $seedScript" -ForegroundColor Cyan
python $seedScript

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Seed completed successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Seed failed with exit code $LASTEXITCODE" -ForegroundColor Red
    Write-Host "Common fixes:" -ForegroundColor Yellow
    Write-Host "  1. Make sure PostgreSQL is running on localhost:5432" -ForegroundColor Yellow
    Write-Host "  2. Make sure the database 'smartattend' exists" -ForegroundColor Yellow
    Write-Host "  3. Check your DATABASE_URL in .env" -ForegroundColor Yellow
    Write-Host "  4. Run: pip install -r apps/backend/requirements.txt" -ForegroundColor Yellow
}
