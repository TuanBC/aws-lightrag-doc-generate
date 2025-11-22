# Quick start script for Windows PowerShell

Write-Host "🚀 Starting Onchain Credit Scoring App..." -ForegroundColor Cyan

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host "⚠️  Warning: .env file not found. Please create one with ETHERSCAN_API_KEY." -ForegroundColor Yellow
    Write-Host "   See README.md for configuration details." -ForegroundColor Yellow
}

# Check if virtual environment exists
if (-not (Test-Path .venv) -and -not (Test-Path venv)) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
}

# Activate virtual environment
if (Test-Path .venv) {
    & .\.venv\Scripts\Activate.ps1
} elseif (Test-Path venv) {
    & .\venv\Scripts\Activate.ps1
}

# Install dependencies
Write-Host "📥 Installing dependencies..." -ForegroundColor Cyan
pip install -q -r requirements.txt

# Run the application
Write-Host "✅ Starting server on http://localhost:8000" -ForegroundColor Green
Write-Host "   Press Ctrl+C to stop" -ForegroundColor Gray
Write-Host ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

