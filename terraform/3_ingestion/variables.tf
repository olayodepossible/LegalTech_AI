variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint from Part 2"
  type        = string
}

variable "vector_index_name" {
  description = "S3 Vectors index name (must match the index you created for this bucket)"
  type        = string
  default     = "legal-research"
}