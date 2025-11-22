# Onchain Credit Scoring - Production Web App

A stateless FastAPI monolith for assessing Ethereum wallet creditworthiness using on-chain transaction analysis. Features an Etherscan-inspired UI and AI-powered reporting.

## 🏗️ Architecture

- **Backend**: FastAPI (stateless monolith)
- **Frontend**: Server-side rendered Jinja2 templates with vanilla JavaScript
- **Styling**: Custom CSS inspired by Etherscan's dark theme
- **Data Sources**: Etherscan API + synthetic off-chain personas
- **Scoring**: Scorecard-based algorithm with 50+ extracted features
- **Reporting**: Optional LLM-powered markdown reports (Claude/GPT via OpenRouter or AWS Bedrock)

## 📋 Features

- ✅ Real-time credit score calculation (0-1000 scale)
- ✅ 50+ on-chain feature extraction
- ✅ Synthetic off-chain persona generation
- ✅ Rate limiting and in-memory caching
- ✅ Client-side address validation and UX enhancements
- ✅ LLM-powered markdown reports (optional)
- ✅ Docker containerization ready
- ✅ Comprehensive test suite

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose (optional, for containerized deployment)
- Etherscan API key ([Get one here](https://etherscan.io/myapikey))
- OpenRouter API key (optional, for LLM reports) ([Get one here](https://openrouter.ai/keys))

### Local Development

1. **Clone and navigate:**
   ```bash
   cd credit_scoring_onchain
   ```

2. **Create environment file:**
   ```bash
   # Create .env file with:
   ETHERSCAN_API_KEY=your_etherscan_key_here
   OPENROUTER_API_KEY=your_openrouter_key_here  # Optional
   OPENROUTER_MODEL=anthropic/claude-3.5-sonnet  # Optional
   LLM_PROVIDER=openrouter  # Optional: 'openrouter' or 'bedrock'
   ```

3. **Install dependencies:**
   ```bash
   # Install uv (if not already installed)
   pip install uv

   # Sync dependencies
   uv sync
   ```

4. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the web app:**
   - Web UI: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/health

### Docker Deployment

1. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build
   ```

2. **Or build and run manually:**
   ```bash
   docker build -t credit-scoring-app .
   docker run -p 8000:8000 --env-file .env credit-scoring-app
   ```

## 📁 Project Structure

```
credit_scoring_onchain/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app factory
│   ├── api/
│   │   └── routes/
│   │       ├── api.py          # JSON API endpoints
│   │       └── web.py          # SSR web routes
│   ├── core/
│   │   ├── config.py           # Settings management
│   │   ├── logging.py          # Logging configuration
│   │   └── llm.py              # LLM provider setup
│   ├── dependencies.py        # FastAPI dependency injection
│   ├── schemas/
│   │   └── score.py            # Pydantic response models
│   ├── services/
│   │   ├── scoring_engine.py   # Main orchestration
│   │   ├── reporting.py        # LLM report generation
│   │   ├── cache.py            # In-memory TTL cache
│   │   └── limiter.py          # Rate limiting
│   ├── static/
│   │   ├── css/
│   │   │   └── etherscan.css   # Etherscan-inspired styles
│   │   └── js/
│   │       └── main.js         # Client-side UX enhancements
│   └── templates/
│       ├── base.html           # Base template
│       ├── home.html           # Landing page
│       └── score_detail.html   # Score results page
├── services/                   # Legacy service modules
│   ├── credit_scoring_service.py
│   ├── etherscan_service.py
│   └── offchain_data_generator.py
├── prompts/
│   └── wallet_report.prompty   # LLM prompt template
├── tests/
│   ├── test_credit_scoring_service.py
│   └── test_scoring_engine.py
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── requirements.txt
└── README.md
```

## 🔌 API Endpoints

### Web Routes (SSR)

- `GET /` - Landing page with address input form
- `POST /scores` - Submit wallet address and view score

### JSON API

- `GET /api/v1/wallets/{wallet_address}/score` - Get credit score and features
- `GET /api/v1/wallets/{wallet_address}/report` - Generate LLM markdown report (requires LLM config)
- `GET /api/health` - Health check endpoint

### Example API Request

```bash
curl http://localhost:8000/api/v1/wallets/0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb/score
```

Response:
```json
{
  "wallet_address": "0x742d35cc6634c0532925a3b844bc9e7595f0beb",
  "breakdown": {
    "credit_score": 642.0,
    "features": {
      "account_age_days": 720,
      "total_transactions": 150,
      "unique_counterparties": 25,
      ...
    },
    "offchain_data": {
      "age": 32,
      "occupation": "professional",
      ...
    },
    "transaction_count": 150
  },
  "message": null
}
```

## 🎯 Credit Score Grading

| Grade | Score Range | Risk Category | Expected Bad Rate |
|-------|-------------|---------------|-------------------|
| 1     | 700+        | Ultra Low Risk (A++) | 0.0% |
| 2     | 653-699     | Very Low Risk (A+) | 1.7% |
| 3     | 600-652     | Low Risk (A) | 2.7% |
| 4     | 570-599     | Moderate Risk (B) | 4.6% |
| 5     | 528-569     | High Risk (C) | 17.3% |
| 6     | <528        | Very High Risk (C-) | 40.4% |

## 🧪 Testing

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app --cov=services
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|-----------|-------------|---------|
| `ETHERSCAN_API_KEY` | Yes | Etherscan API key | - |
| `OPENROUTER_API_KEY` | No | OpenRouter API key for LLM reports | - |
| `OPENROUTER_MODEL` | No | Model identifier | `anthropic/claude-3.5-sonnet` |
| `LLM_PROVIDER` | No | LLM provider: `openrouter` or `bedrock` | `openrouter` |
| `BEDROCK_MODEL_ID` | No | AWS Bedrock model ID | `anthropic.claude-3-5-sonnet-20240620-v1:0` |
| `BEDROCK_REGION` | No | AWS region for Bedrock | `us-east-1` |
| `AWS_BEARER_TOKEN_BEDROCK` | No | AWS bearer token for Bedrock | - |
| `ENVIRONMENT` | No | Deployment environment | `local` |

### Rate Limiting

Default: 10 requests per minute per IP. Configure in `app/services/limiter.py`.

### Caching

Default: 5-minute TTL, 1000 max items. Configure in `app/services/cache.py`.

## 🚢 Production Deployment

### Docker

1. Build production image:
   ```bash
   docker build -t credit-scoring-app:latest .
   ```

2. Run with environment variables:
   ```bash
   docker run -d \
     -p 8000:8000 \
     -e ETHERSCAN_API_KEY=your_key \
     -e OPENROUTER_API_KEY=your_key \
     --name credit-scoring \
     credit-scoring-app:latest
   ```

### Reverse Proxy (NGINX)

Example NGINX configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Environment-Specific Settings

- **Development**: Use `--reload` flag for auto-reload
- **Production**: Set `ENVIRONMENT=production` and disable debug features
- **Scaling**: Run multiple containers behind a load balancer (stateless design supports horizontal scaling)

## 🛠️ Development

### Code Quality

```bash
# Linting
ruff check

# Formatting
ruff format
```

### Dependency Management

This project uses `uv` for fast dependency management.

```bash
# Add a new package
uv add package_name

# Add a development dependency
uv add --dev package_name

# Remove a package
uv remove package_name

# Sync environment with pyproject.toml
uv sync
```

### Adding New Features

1. **New API endpoint**: Add to `app/api/routes/api.py` or `web.py`
2. **New service**: Add to `app/services/`
3. **New template**: Add to `app/templates/` and extend `base.html`
4. **New static asset**: Add to `app/static/`

## 📝 License

[Add your license here]

## 🤝 Contributing

[Add contribution guidelines here]
