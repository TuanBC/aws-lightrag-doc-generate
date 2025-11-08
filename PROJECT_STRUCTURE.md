# Project Structure Overview

```
final_code/
│
├── main.py                           # FastAPI application entry point
│   └── Defines the /v1/wallet/:wallet_address/enquiry endpoint
│
├── services/                         # Business logic modules
│   ├── __init__.py
│   ├── etherscan_service.py         # Etherscan API client
│   │   ├── EtherscanService class
│   │   ├── fetch_transactions()     # Get transaction history
│   │   └── fetch_card_info()        # Get additional wallet info
│   │
│   └── credit_scoring_service.py    # Feature extraction & scoring
│       ├── CreditScoringService class
│       ├── extract_features()       # Extract 60+ credit features
│       └── calculate_credit_score() # Compute final score
│
├── requirements.txt                  # Python dependencies
├── .env.example                      # Environment variables template
├── .gitignore                        # Git ignore rules
│
├── README.md                         # Complete documentation
├── QUICKSTART.md                     # Quick start guide
│
├── start_server.ps1                  # PowerShell script to start server
└── example_usage.py                  # Example usage script
```

## Key Components

### 1. main.py
- FastAPI application initialization
- Route definitions
- Request/response models
- Error handling

### 2. services/etherscan_service.py
- Asynchronous API calls to Etherscan
- Transaction history pagination
- Card information scraping
- Rate limiting handling

### 3. services/credit_scoring_service.py
- Feature extraction from transaction data
- 60+ features including:
  - Account age and activity
  - Transaction volumes and patterns
  - Counterparty analysis
  - Contract interactions
  - Temporal patterns
  - Risk indicators
- Credit score calculation algorithm

## Data Flow

```
Client Request
    ↓
[FastAPI Endpoint]
    ↓
[EtherscanService.fetch_transactions()]
    ↓
[CreditScoringService.extract_features()]
    ↓
[CreditScoringService.calculate_credit_score()]
    ↓
[Response with credit_score + features]
```

## Features Extracted

1. **Basic Metrics**
   - account_age_days
   - total_transactions
   - avg_tx_per_month

2. **Financial Metrics**
   - total_eth_sent/received
   - net_eth_change
   - largest/avg/median_tx_value

3. **Behavioral Metrics**
   - unique_counterparties
   - contract_interactions
   - failed_tx_ratio
   - activity patterns

4. **Temporal Metrics**
   - days_since_last_tx
   - active_days
   - max_inactivity_days
   - 6-month and 12-month metrics

5. **Risk Indicators**
   - failed_tx_ratio
   - max_failed_tx_streak
   - automated_activity

## Credit Score Calculation

The score (0-1000) is based on:
- Account Age (200 pts)
- Transaction Activity (200 pts)
- ETH Volume (200 pts)
- Counterparty Diversity (150 pts)
- Contract Interactions (100 pts)
- Recent Activity (50 pts)
- Activity Consistency (100 pts)
- Failed Transaction Penalty (-100 pts)
- Card Info Bonus (variable)

## API Response Schema

```json
{
  "wallet_address": "string",
  "credit_score": "float (0-1000)",
  "features": {
    "account_age_days": "int",
    "total_transactions": "int",
    "total_eth_sent": "float",
    ...
  },
  "card_info": {
    "card_credit_score": "int",
    "card_reputation_score": "int",
    ...
  },
  "message": "string"
}
```

## Environment Variables

- `ETHERSCAN_API_KEY`: Required - Your Etherscan API key

## Dependencies

- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **pydantic**: Data validation
- **aiohttp**: Async HTTP client
- **pandas**: Data processing
- **beautifulsoup4**: HTML parsing
- **python-dotenv**: Environment management
