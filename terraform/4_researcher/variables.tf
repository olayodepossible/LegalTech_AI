variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key for the researcher agent"
  type        = string
  sensitive   = true
}

variable "finPlex_api_endpoint" {
  description = "FinPlex API endpoint from Part 3"
  type        = string
}

variable "finPlex_api_key" {
  description = "FinPlex API key from Part 3"
  type        = string
  sensitive   = true
}

variable "scheduler_enabled" {
  description = "Enable automated research scheduler"
  type        = bool
  default     = false
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