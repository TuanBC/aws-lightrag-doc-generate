# Terraform Infrastructure - AWS App Runner

Cost-optimized deployment using AWS App Runner (~$5-15/month).

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   GitHub    │────▶│     ECR     │────▶│   App Runner    │
│   Actions   │     │  Registry   │     │   (0.25 vCPU)   │
└─────────────┘     └─────────────┘     └─────────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  Secrets    │
                                        │  Manager    │
                                        └─────────────┘
```

## Cost Breakdown

| Resource | Monthly Cost |
|----------|-------------|
| App Runner (0.25 vCPU, 0.5GB) | ~$5-12 |
| ECR Storage | ~$0.10 |
| Secrets Manager | ~$0.80 |
| **Total** | **~$6-15/month** |

## Prerequisites

1. Terraform >= 1.0
2. AWS CLI configured
3. Docker image in ECR (push first via GitHub Actions)

## Quick Start

```bash
cd aws/terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars << EOF
aws_region         = "ap-southeast-2"
etherscan_api_key  = "your-etherscan-api-key"
openrouter_api_key = "your-openrouter-api-key"
EOF

terraform apply
```

## First-Time Setup

1. **Push Docker image first** (App Runner needs an image to start):
   ```bash
   # Login to ECR
   aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com
   
   # Build and push
   docker build -t credit-scoring-onchain .
   docker tag credit-scoring-onchain:latest YOUR_ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com/credit-scoring-onchain:latest
   docker push YOUR_ACCOUNT_ID.dkr.ecr.ap-southeast-2.amazonaws.com/credit-scoring-onchain:latest
   ```

2. **Apply Terraform**:
   ```bash
   terraform apply
   ```

3. **Get your URL**:
   ```bash
   terraform output app_runner_service_url
   ```

## Outputs

| Output | Description |
|--------|-------------|
| `ecr_repository_url` | ECR URL for Docker pushes |
| `app_runner_service_url` | Your app's public URL |
| `app_runner_service_arn` | ARN for deployments |

## Deploying Updates

After initial setup, just push to `main` branch. GitHub Actions will:
1. Build Docker image
2. Push to ECR
3. Trigger App Runner deployment

## Destroying

```bash
terraform destroy
```

## Files

- `main.tf` - App Runner configuration
- `variables.tf` - Input variables
- `main.tf.ecs-backup` - Old ECS configuration (backup)


