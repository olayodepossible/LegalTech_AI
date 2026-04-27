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

# Align with terraform/2_sagemaker and terraform/3_ingestion (RAG retrieval in legal chat)
variable "sagemaker_endpoint_name" {
  description = "SageMaker embedding endpoint name (same as Part 2 / Part 3 ingest)"
  type        = string
}

variable "vector_index_name" {
  description = "S3 Vectors index name (same as 3_ingestion var.vector_index_name)"
  type        = string
  default     = "legal-research"
}