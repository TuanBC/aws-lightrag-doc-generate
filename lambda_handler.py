"""AWS Lambda handler using Mangum adapter for FastAPI."""

from mangum import Mangum

from app.main import app

# Mangum wraps FastAPI for Lambda/API Gateway
handler = Mangum(app, lifespan="off")
