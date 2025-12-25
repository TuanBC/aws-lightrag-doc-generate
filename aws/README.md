# AWS Deployment Guide - Technical Document Generator (Zero-Scale)

This guide deploys using **Lambda + S3** for zero-cost-when-idle architecture.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   S3 Static     │     │  Lambda + URL   │
│   (Frontend)    │────▶│   (Backend)     │
│   $0 storage    │     │   $0 idle       │
└─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────┐
                        │   Bedrock   │
                        │  (per-use)  │
                        └─────────────┘
```

## Cost Comparison

| Architecture | Idle Cost | Active Cost |
|--------------|-----------|-------------|
| App Runner | ~$15/month | ~$15-30/month |
| **Lambda (this)** | **$0** | ~$0.50-5/month |

## Prerequisites

- AWS CLI configured
- Terraform >= 1.0
- Docker

## Quick Start

### Step 1: Initialize Terraform

```bash
cd aws/terraform
terraform init
terraform apply
```

### Step 2: Build & Push Lambda Image

```powershell
# Get ECR URL from terraform output
$ECR_URL = terraform output -raw ecr_repository_url

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URL

# Build Lambda image
docker build -f Dockerfile.lambda -t tech-doc-lambda .

# Tag and push
docker tag tech-doc-lambda:latest ${ECR_URL}:latest
docker push ${ECR_URL}:latest

# Update Lambda function
aws lambda update-function-code --function-name tech-doc-generator --image-uri ${ECR_URL}:latest
```

### Step 3: Deploy Frontend (Optional)

```powershell
# Build static frontend
# (If using separate SPA, build it first)

# Upload to S3
$BUCKET = terraform output -raw frontend_bucket_name
aws s3 sync ./frontend/dist s3://$BUCKET --delete
```

### Step 4: Get URLs

```bash
# Backend API URL
terraform output lambda_function_url

# Frontend URL
terraform output frontend_bucket_url
```

## Testing

```powershell
# Get the Lambda URL
$API_URL = terraform output -raw lambda_function_url

# Test health
curl "${API_URL}api/health"

# Generate document
Invoke-RestMethod -Uri "${API_URL}api/v1/documents/generate" -Method POST -ContentType "application/json" -Body '{"document_type":"srs","library_name":"fastapi"}'
```

## Cold Start Optimization

Lambda cold starts are ~3-5 seconds. To reduce:

1. **Provisioned Concurrency** (adds cost):
```hcl
resource "aws_lambda_provisioned_concurrency_config" "app" {
  function_name                     = aws_lambda_function.app.function_name
  provisioned_concurrent_executions = 1
  qualifier                         = aws_lambda_function.app.version
}
```

2. **Keep-alive ping** (free): Use CloudWatch Events to ping every 5 minutes

## Cleanup

```bash
terraform destroy
```
