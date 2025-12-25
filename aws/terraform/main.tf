# =============================================================================
# Terraform configuration for Technical Document Generator (ZERO-SCALE)
# AWS Resources: Lambda + API Gateway + S3 (Static Frontend)
# Costs $0 when idle, pay only per request
# =============================================================================

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  function_name = "tech-doc-generator"
  api_name      = "tech-doc-api"
}

# =============================================================================
# S3 Bucket for Static Frontend (Optional)
# =============================================================================

resource "aws_s3_bucket" "frontend" {
  bucket        = "tech-doc-frontend-${data.aws_caller_identity.current.account_id}"
  force_destroy = true

  tags = {
    Name      = "tech-doc-frontend"
    ManagedBy = "terraform"
  }
}

resource "aws_s3_bucket_website_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}

# =============================================================================
# ECR Repository (for Lambda container image)
# =============================================================================

resource "aws_ecr_repository" "app" {
  name                 = local.function_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep only last 3 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 3
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# =============================================================================
# S3 Bucket for LightRAG Data (Graph Index)
# =============================================================================

resource "aws_s3_bucket" "lightrag_data" {
  bucket        = "tech-doc-lightrag-${data.aws_caller_identity.current.account_id}"
  force_destroy = true

  tags = {
    Name      = "tech-doc-lightrag-data"
    ManagedBy = "terraform"
  }
}

resource "aws_s3_bucket_versioning" "lightrag_data" {
  bucket = aws_s3_bucket.lightrag_data.id
  versioning_configuration {
    status = "Enabled"
  }
}

# =============================================================================
# IAM Role for Lambda
# =============================================================================

resource "aws_iam_role" "lambda_role" {
  name = "${local.function_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "${local.function_name}-bedrock-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.bedrock_region}::foundation-model/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:tech-doc/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.lightrag_data.arn,
          "${aws_s3_bucket.lightrag_data.arn}/*"
        ]
      }
    ]
  })
}

# =============================================================================
# Lambda Function (Container Image)
# =============================================================================

resource "aws_lambda_function" "app" {
  function_name = local.function_name
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  timeout       = 300  # 5 minutes for LLM calls
  memory_size   = 1024 # 1GB for faster cold starts

  environment {
    variables = {
      ENVIRONMENT        = "production"
      LLM_PROVIDER       = "bedrock"
      BEDROCK_MODEL_ID   = var.bedrock_model_id
      BEDROCK_REGION     = var.bedrock_region
      CONTEXT7_MCP_URL   = "https://mcp.context7.com/mcp"
      CONTEXT7_API_KEY   = var.context7_api_key
      LIGHTRAG_S3_BUCKET = aws_s3_bucket.lightrag_data.bucket
    }
  }

  # Ignore image_uri changes (deploy separately)
  lifecycle {
    ignore_changes = [image_uri]
  }

  tags = {
    Name        = local.function_name
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# =============================================================================
# Lambda Function URL (Simpler than API Gateway)
# =============================================================================

resource "aws_lambda_function_url" "app" {
  function_name      = aws_lambda_function.app.function_name
  authorization_type = "NONE"

  cors {
    allow_origins     = ["*"]
    allow_methods     = ["*"]
    allow_headers     = ["*"]
    max_age           = 86400
  }
}

# =============================================================================
# CloudWatch Log Group
# =============================================================================

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.function_name}"
  retention_in_days = 7  # Keep logs for 7 days only (cost saving)
}

# =============================================================================
# Secrets Manager (Optional)
# =============================================================================

resource "aws_secretsmanager_secret" "context7_api_key" {
  count                   = var.context7_api_key != "" ? 1 : 0
  name                    = "tech-doc/context7-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "context7_api_key" {
  count         = var.context7_api_key != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.context7_api_key[0].id
  secret_string = var.context7_api_key
}

# =============================================================================
# Outputs
# =============================================================================

output "ecr_repository_url" {
  description = "ECR repository URL for Docker pushes"
  value       = aws_ecr_repository.app.repository_url
}

output "lambda_function_url" {
  description = "Lambda Function URL (Backend API)"
  value       = aws_lambda_function_url.app.function_url
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.app.arn
}

output "frontend_bucket_url" {
  description = "S3 static website URL (Frontend)"
  value       = "http://${aws_s3_bucket.frontend.bucket}.s3-website-${var.aws_region}.amazonaws.com"
}

output "frontend_bucket_name" {
  description = "S3 bucket name for frontend deployment"
  value       = aws_s3_bucket.frontend.bucket
}

output "lightrag_bucket_name" {
  description = "S3 bucket for LightRAG graph index"
  value       = aws_s3_bucket.lightrag_data.bucket
}
