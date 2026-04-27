variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "eu-west-2"
}

# Clerk validation happens in Lambda, not at API Gateway level
variable "clerk_jwks_url" {
  description = "Clerk JWKS URL for JWT validation in Lambda"
  type        = string
}

variable "clerk_issuer" {
  description = "Clerk issuer URL (kept for Lambda environment)"
  type        = string
  default     = ""  # Not actually used but kept for backwards compatibility
}

# Contract analysis (POST /api/contracts/analyze) via OpenRouter
variable "openrouter_api_key" {
  description = "OpenRouter API key for contract analysis and other API routes that call OpenRouter"
  type        = string
  sensitive   = true
}