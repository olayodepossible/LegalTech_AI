variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key for the researcher agent"
  type        = string
  sensitive   = true
}

variable "legal_api_endpoint" {
  description = "Legal API endpoint"
  type        = string
}

variable "legal_api_key" {
  description = "Legal API key"
  type        = string
  sensitive   = true
}


variable "openrouter_api_key" {
  description = "Openrouter API key for Agents SDK"
  type        = string
  sensitive   = true
  validation {
    condition     = length(trimspace(var.openrouter_api_key)) >= 8
    error_message = "openrouter_api_key must be a non-empty secret (set OPENROUTER_API_KEY or TF_VAR_openrouter_api_key)."
  }
}

# LiteLLM: openrouter/openai/<id> in backend/researcher/research_evaluation.py — align with .env OPENAI_CHAT_MODEL
variable "openai_chat_model" {
  description = "OpenAI-compatible model id on OpenRouter (e.g. gpt-4.1-mini, gpt-4o-mini)"
  type        = string
  default     = "gpt-4.1-mini"
}