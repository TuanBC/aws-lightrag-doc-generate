# Quick Start Guide

## Setup (First Time Only)

1. **Get an Etherscan API Key**
   - Go to https://etherscan.io/myapikey
   - Sign up/login and create a new API key
   - Copy your API key

2. **Configure Environment**
   ```powershell
   # Copy the example environment file
   Copy-Item .env.example .env
   
   # Edit .env and add your API key
   notepad .env
   # Replace 'your_etherscan_api_key_here' with your actual API key
   ```

3. **Install Dependencies**
   ```powershell
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   .\venv\Scripts\Activate.ps1
   
   # Install requirements
   pip install -r requirements.txt
   ```

## Running the Server

### Option 1: Using the PowerShell Script (Recommended)
```powershell
.\start_server.ps1
```

### Option 2: Manual Start
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start server
uvicorn main:app --reload
```

The server will start at: http://localhost:8000

## Testing the API

### Using a Web Browser
1. Open http://localhost:8000/docs (Swagger UI)
2. Click on the `/v1/wallet/{wallet_address}/enquiry` endpoint
3. Click "Try it out"
4. Enter a wallet address (e.g., `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`)
5. Click "Execute"

### Using curl
```powershell
curl http://localhost:8000/v1/wallet/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb/enquiry
```

### Using the Example Script
```powershell
python example_usage.py
```

## Example Response

```json
{
  "wallet_address": "0x742d35cc6634c0532925a3b844bc9e7595f0beb",
  "credit_score": 687.42,
  "features": {
    "account_age_days": 2157,
    "total_transactions": 335,
    "total_eth_sent": 6405.94,
    "total_eth_received": 2.0,
    "net_eth_change": -6403.94,
    "unique_counterparties": 27,
    "contract_interactions": 321,
    "failed_tx_ratio": 0.036
  },
  "message": "Credit score calculated successfully"
}
```

## Troubleshooting

### "ETHERSCAN_API_KEY not found"
- Make sure you created the `.env` file from `.env.example`
- Verify your API key is correctly set in the `.env` file

### "Module not found" errors
- Make sure you activated the virtual environment
- Run `pip install -r requirements.txt` again

### Slow response times
- First request may be slow due to fetching all transaction history
- Etherscan API has rate limits (5 calls/second for free tier)
- Wallets with many transactions take longer to process

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root endpoint with API info |
| `/health` | GET | Health check |
| `/v1/wallet/{wallet_address}/enquiry` | GET | Get credit score for wallet |
| `/docs` | GET | Swagger UI documentation |
| `/redoc` | GET | ReDoc documentation |

## Next Steps

- See `README.md` for detailed documentation
- Modify `services/credit_scoring_service.py` to customize the scoring algorithm
- Add authentication/authorization for production deployment
- Implement caching to reduce API calls
- Add database storage for historical scores
