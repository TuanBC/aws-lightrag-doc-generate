# =============================================================================
# Variables for Technical Document Generator Infrastructure (LITE)
# =============================================================================

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

# =============================================================================
# Context7 Configuration
# =============================================================================

variable "context7_api_key" {
  description = "Context7 API key for higher rate limits (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

# =============================================================================
# Bedrock Configuration
# =============================================================================

variable "bedrock_model_id" {
  description = "AWS Bedrock Chat Model ID"
  type        = string
  default     = "amazon.nova-pro-v1:0"
}

variable "bedrock_region" {
  description = "AWS Bedrock region (may differ from main region)"
  type        = string
  default     = "us-east-1"
}

# =============================================================================
# Optional: OpenRouter (fallback LLM)
# =============================================================================

variable "openrouter_api_key" {
  description = "OpenRouter API key (optional, for fallback LLM)"
  type        = string
  sensitive   = true
  default     = ""
}
