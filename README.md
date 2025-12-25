# Technical Document Generator

AI-powered technical document generation using Context7 MCP and AWS Bedrock. Generate SRS, Functional Specs, and technical documentation with Mermaid diagrams.

## 🏗️ Architecture

- **Backend**: FastAPI (stateless monolith)
- **Frontend**: Server-side rendered Jinja2 templates
- **LLM**: Amazon Bedrock (Nova Pro v1:0)
- **Embeddings**: Amazon Titan Embed Text v2
- **Vector Store**: Bedrock Knowledge Base + OpenSearch Serverless
- **Documentation**: Context7 MCP (remote)

## 📋 Features

- ✅ Generate SRS documents from library documentation
- ✅ Generate Functional Specifications with Mermaid diagrams
- ✅ Context7 MCP integration for up-to-date library docs
- ✅ Bedrock Knowledge Base for RAG with uploaded documents
- ✅ Critic agent for markdown/mermaid validation
- ✅ Docker containerization ready
- ✅ Terraform infrastructure as code

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- AWS Account with Bedrock access
- Docker (optional)

### Local Development

1. **Clone and navigate:**
   ```bash
   cd technical-doc-generator
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Install dependencies:**
   ```bash
   pip install uv
   uv sync
   ```

4. **Run the application:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the web app:**
   - Web UI: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### AWS Deployment

See [aws/README.md](aws/README.md) for Terraform deployment instructions.

## 📁 Project Structure

```
technical-doc-generator/
├── app/
│   ├── main.py                 # FastAPI app factory
│   ├── api/routes/
│   │   ├── api.py              # JSON API endpoints
│   │   └── web.py              # SSR web routes
│   ├── core/
│   │   ├── config.py           # Settings management
│   │   └── llm.py              # LLM provider setup
│   ├── services/
│   │   ├── context7_service.py # Context7 MCP client
│   │   ├── knowledge_base_service.py
│   │   ├── document_generator.py
│   │   └── critic_agent.py
│   ├── static/                 # CSS, JS assets
│   └── templates/              # Jinja2 templates
├── prompts/
│   ├── srs_template.prompty
│   ├── functional_spec.prompty
│   └── critic_prompt.prompty
├── aws/
│   ├── terraform/              # Infrastructure as code
│   └── README.md               # Deployment guide
└── tests/
```

## 🔌 API Endpoints

### Web Routes (SSR)
- `GET /` - Landing page with document generation form
- `POST /generate` - Generate document and show progress

### JSON API
- `POST /api/v1/documents/generate` - Generate document
- `POST /api/v1/documents/validate` - Validate markdown/mermaid
- `POST /api/v1/documents/upload` - Upload to Knowledge Base
- `GET /api/health` - Health check

## 🔧 Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `CONTEXT7_MCP_URL` | No | Context7 MCP URL (default: remote) |
| `CONTEXT7_API_KEY` | No | Context7 API key for higher limits |
| `BEDROCK_MODEL_ID` | No | Chat model (default: nova-pro-v1:0) |
| `BEDROCK_KB_ID` | No | Knowledge Base ID |
| `LLM_PROVIDER` | No | 'bedrock' or 'openrouter' |

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app
```

## 📝 License

MIT
