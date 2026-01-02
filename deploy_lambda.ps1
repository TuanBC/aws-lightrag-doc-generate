# Deploy RAG-Anything to AWS Lambda
# Run this script from the project root directory

# Variables (from Terraform outputs)
$ECR_URL = "043229137291.dkr.ecr.us-east-1.amazonaws.com/tech-doc-generator"
$LAMBDA_NAME = "tech-doc-generator"
$REGION = "us-east-1"

# 1. Login to ECR
Write-Host "Logging in to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URL.Split('/')[0]

# 2. Build Docker image
Write-Host "Building Docker image..."
docker build -f Dockerfile.lambda -t tech-doc-generator .

# 3. Tag for ECR
Write-Host "Tagging image..."
docker tag tech-doc-generator:latest ${ECR_URL}:latest

# 4. Push to ECR
Write-Host "Pushing to ECR..."
docker push ${ECR_URL}:latest

# 5. Update Lambda function
Write-Host "Updating Lambda function..."
aws lambda update-function-code `
    --function-name $LAMBDA_NAME `
    --image-uri ${ECR_URL}:latest `
    --region $REGION

Write-Host "`n=== Deployment Complete ===" -ForegroundColor Green
Write-Host "Lambda URL: https://$(aws lambda get-function-url-config --function-name $LAMBDA_NAME --region $REGION --query 'FunctionUrl' --output text)"
