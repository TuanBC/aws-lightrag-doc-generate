# Terraform configuration for AWS App Runner (Cost-Optimized)
# Estimated cost: ~$5-15/month for low traffic

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

# ============================================
# ECR Repository (reuse existing or create)
# ============================================
resource "aws_ecr_repository" "app" {
  name                 = "credit-scoring-onchain"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Allow deletion even with images

  image_scanning_configuration {
    scan_on_push = true
  }

  # Lifecycle policy to save storage costs
  lifecycle {
    prevent_destroy = false
  }
}

# ECR Lifecycle Policy - Keep only last 3 images to save costs
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

# ============================================
# IAM Role for App Runner ECR Access
# ============================================
resource "aws_iam_role" "apprunner_ecr_access" {
  name = "apprunner-ecr-access-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  role       = aws_iam_role.apprunner_ecr_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# ============================================
# IAM Role for App Runner Instance
# ============================================
resource "aws_iam_role" "apprunner_instance" {
  name = "apprunner-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

# Policy for Secrets Manager access
resource "aws_iam_role_policy" "apprunner_secrets" {
  name = "apprunner-secrets-access"
  role = aws_iam_role.apprunner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:credit-scoring/*"
        ]
      }
    ]
  })
}

# ============================================
# Secrets Manager (Environment Variables)
# ============================================
resource "aws_secretsmanager_secret" "etherscan_api_key" {
  name                    = "credit-scoring/etherscan-api-key"
  recovery_window_in_days = 0  # Immediate deletion (cost saving)
}

resource "aws_secretsmanager_secret_version" "etherscan_api_key" {
  secret_id     = aws_secretsmanager_secret.etherscan_api_key.id
  secret_string = var.etherscan_api_key
}

# OpenRouter is optional - only create if provided
resource "aws_secretsmanager_secret" "openrouter_api_key" {
  count                   = var.openrouter_api_key != "" ? 1 : 0
  name                    = "credit-scoring/openrouter-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "openrouter_api_key" {
  count         = var.openrouter_api_key != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.openrouter_api_key[0].id
  secret_string = var.openrouter_api_key
}

resource "aws_secretsmanager_secret" "bedrock_bearer_token" {
  name                    = "credit-scoring/bedrock-bearer-token"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "bedrock_bearer_token" {
  secret_id     = aws_secretsmanager_secret.bedrock_bearer_token.id
  secret_string = var.bedrock_bearer_token
}

# ============================================
# App Runner Service (Cost-Optimized)
# ============================================
resource "aws_apprunner_service" "app" {
  service_name = "credit-scoring-app"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_configuration {
        port = "8000"
        
        runtime_environment_variables = {
          ENVIRONMENT      = "production"
          LLM_PROVIDER     = "bedrock"
          BEDROCK_MODEL_ID = var.bedrock_model_id
          BEDROCK_REGION   = var.bedrock_region
        }

        runtime_environment_secrets = merge(
          {
            ETHERSCAN_API_KEY        = aws_secretsmanager_secret.etherscan_api_key.arn
            AWS_BEARER_TOKEN_BEDROCK = aws_secretsmanager_secret.bedrock_bearer_token.arn
          },
          var.openrouter_api_key != "" ? {
            OPENROUTER_API_KEY = aws_secretsmanager_secret.openrouter_api_key[0].arn
          } : {}
        )
      }

      image_identifier      = "${aws_ecr_repository.app.repository_url}:latest"
      image_repository_type = "ECR"
    }

    auto_deployments_enabled = false  # Manual deployments via GitHub Actions
  }

  instance_configuration {
    # COST OPTIMIZATION: Smallest instance
    cpu    = "256"   # 0.25 vCPU (minimum)
    memory = "512"   # 0.5 GB (minimum)
    
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  # COST OPTIMIZATION: Scale to minimum
  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.cost_optimized.arn

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/api/health"
    interval            = 20  # Longer interval = less health check overhead
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  tags = {
    Name        = "credit-scoring-app"
    Environment = "production"
    ManagedBy   = "terraform"
  }
}

# ============================================
# Auto Scaling Configuration (Cost-Optimized)
# ============================================
resource "aws_apprunner_auto_scaling_configuration_version" "cost_optimized" {
  auto_scaling_configuration_name = "cost-optimized"

  # COST OPTIMIZATION: Keep instances to minimum
  min_size = 1  # Minimum 1 instance (can't go to 0)
  max_size = 2  # Cap at 2 for unexpected traffic

  max_concurrency = 100  # Requests per instance before scaling

  tags = {
    Name = "cost-optimized-scaling"
  }
}

# ============================================
# Outputs
# ============================================
output "ecr_repository_url" {
  description = "ECR repository URL for Docker pushes"
  value       = aws_ecr_repository.app.repository_url
}

output "app_runner_service_url" {
  description = "App Runner service URL"
  value       = aws_apprunner_service.app.service_url
}

output "app_runner_service_arn" {
  description = "App Runner service ARN for deployments"
  value       = aws_apprunner_service.app.arn
}

output "app_runner_service_id" {
  description = "App Runner service ID"
  value       = aws_apprunner_service.app.service_id
}

