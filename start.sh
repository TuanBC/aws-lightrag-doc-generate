#!/bin/bash
# Quick start script for local development

set -e

echo "🚀 Starting Onchain Credit Scoring App..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Please create one with ETHERSCAN_API_KEY."
    echo "   See README.md for configuration details."
fi

# Check if virtual environment exists
if [ ! -d ".venv" ] && [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv .venv
fi

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Run the application
echo "✅ Starting server on http://localhost:8000"
echo "   Press Ctrl+C to stop"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

