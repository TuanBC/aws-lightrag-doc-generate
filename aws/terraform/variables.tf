variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "etherscan_api_key" {
  description = "Etherscan API key"
  type        = string
  sensitive   = true
}

variable "openrouter_api_key" {
  description = "OpenRouter API key (optional)"
  type        = string
  sensitive   = true
  default     = ""
}

