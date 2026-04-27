terraform {
  required_version = ">= 1.5"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Using local backend - state will be stored in terraform.tfstate in this directory
  # This is automatically gitignored for security
}

provider "aws" {
  region = var.aws_region
}

# Data source for current caller identity
data "aws_caller_identity" "current" {}

# ========================================
# S3 Vectors Bucket
# ========================================

resource "aws_s3_bucket" "vectors" {
  bucket = "legal-companion-vectors-${data.aws_caller_identity.current.account_id}"
  
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

resource "aws_s3_bucket_versioning" "vectors" {
  bucket = aws_s3_bucket.vectors.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "vectors" {
  bucket = aws_s3_bucket.vectors.id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "vectors" {
  bucket = aws_s3_bucket.vectors.id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ========================================
# Lambda Function for Ingestion
# ========================================

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "legal-companion-ingest-lambda-role"
  
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
  
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

# Lambda policy for S3 Vectors and SageMaker
resource "aws_iam_role_policy" "lambda_policy" {
  name = "legal-companion-ingest-lambda-policy"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.vectors.arn,
          "${aws_s3_bucket.vectors.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sagemaker:InvokeEndpoint"
        ]
        Resource = "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:endpoint/${var.sagemaker_endpoint_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "s3vectors:PutVectors",
          "s3vectors:QueryVectors",
          "s3vectors:GetVectors",
          "s3vectors:DeleteVectors"
        ]
        Resource = "arn:aws:s3vectors:${var.aws_region}:${data.aws_caller_identity.current.account_id}:bucket/${aws_s3_bucket.vectors.id}/index/*"
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "ingest" {
  function_name = "legal-companion-ingest"
  role          = aws_iam_role.lambda_role.arn
  
  # Note: The deployment package will be created by the guide instructions
  filename         = "${path.module}/../../backend/ingest/lambda_function.zip"
  source_code_hash = fileexists("${path.module}/../../backend/ingest/lambda_function.zip") ? filebase64sha256("${path.module}/../../backend/ingest/lambda_function.zip") : null
  
  handler = "ingest_s3vectors.lambda_handler"
  runtime = "python3.12"
  timeout = 60
  memory_size = 512
  
  environment {
    variables = {
      VECTOR_BUCKET      = aws_s3_bucket.vectors.id
      SAGEMAKER_ENDPOINT = var.sagemaker_endpoint_name
      INDEX_NAME           = var.vector_index_name
    }
  }
  
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/legal-companion-ingest"
  retention_in_days = 7
  
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

# ========================================
# API Gateway
# ========================================

# REST API
resource "aws_api_gateway_rest_api" "api" {
  name        = "legal-companion-api"
  description = "legal-companion Planner API"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

# API Resource
resource "aws_api_gateway_resource" "ingest" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "ingest"
}

# API Method
resource "aws_api_gateway_method" "ingest_post" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.ingest.id
  http_method   = "POST"
  authorization = "NONE"
  api_key_required = true
}

# Lambda Integration
resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.ingest.id
  http_method = aws_api_gateway_method.ingest_post.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.ingest.invoke_arn
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}

# API Deployment
resource "aws_api_gateway_deployment" "api" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.ingest.id,
      aws_api_gateway_method.ingest_post.id,
      aws_api_gateway_integration.lambda.id,
    ]))
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# API Stage
resource "aws_api_gateway_stage" "api" {
  deployment_id = aws_api_gateway_deployment.api.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "prod"
  
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

# API Key
resource "aws_api_gateway_api_key" "api_key" {
  name = "legal-companion-api-key"
  
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

# Usage Plan
resource "aws_api_gateway_usage_plan" "plan" {
  name = "legal-companion-usage-plan"
  
  api_stages {
    api_id = aws_api_gateway_rest_api.api.id
    stage  = aws_api_gateway_stage.api.stage_name
  }
  
  quota_settings {
    limit  = 10000
    period = "MONTH"
  }
  
  throttle_settings {
    rate_limit  = 100
    burst_limit = 200
  }
}

# Usage Plan Key
resource "aws_api_gateway_usage_plan_key" "plan_key" {
  key_id        = aws_api_gateway_api_key.api_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.plan.id
}

# ========================================
# RAG document ingest (S3 upload -> chunks -> S3 Vectors)
# ========================================

resource "aws_sqs_queue" "rag_ingest_dlq" {
  name = "legal-companion-rag-ingest-dlq"
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

resource "aws_sqs_queue" "rag_ingest" {
  name                       = "legal-companion-rag-ingest"
  visibility_timeout_seconds = 360
  message_retention_seconds  = 86400
  receive_wait_time_seconds  = 10
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.rag_ingest_dlq.arn
    maxReceiveCount     = 3
  })
  tags = {
    Project = "legal-companion"
    Part    = "3"
  }
}

# Dedicated role: worker reads user uploads, writes vectors
resource "aws_iam_role" "rag_worker" {
  name = "legal-companion-rag-worker-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
  tags = { Project = "legal-companion", Part = "3" }
}

resource "aws_iam_role_policy" "rag_worker" {
  name = "legal-companion-rag-worker-policy"
  role = aws_iam_role.rag_worker.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      },
      {
        Effect = "Allow"
        Action = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.vectors.arn}/*"
      },
      {
        Effect = "Allow"
        Action = ["sagemaker:InvokeEndpoint"]
        Resource = "arn:aws:sagemaker:${var.aws_region}:${data.aws_caller_identity.current.account_id}:endpoint/${var.sagemaker_endpoint_name}"
      },
      {
        Effect = "Allow"
        Action = [
          "s3vectors:PutVectors",
          "s3vectors:QueryVectors"
        ]
        Resource = "arn:aws:s3vectors:${var.aws_region}:${data.aws_caller_identity.current.account_id}:bucket/${aws_s3_bucket.vectors.id}/index/*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.rag_ingest.arn
      }
    ]
  })
}

resource "aws_cloudwatch_log_group" "rag_worker" {
  name              = "/aws/lambda/legal-companion-rag-ingest-worker"
  retention_in_days = 14
  tags              = { Project = "legal-companion", Part = "3" }
}

resource "aws_lambda_function" "rag_ingest_worker" {
  function_name    = "legal-companion-rag-ingest-worker"
  role             = aws_iam_role.rag_worker.arn
  filename         = "${path.module}/../../backend/ingest/lambda_function.zip"
  source_code_hash = fileexists("${path.module}/../../backend/ingest/lambda_function.zip") ? filebase64sha256("${path.module}/../../backend/ingest/lambda_function.zip") : null
  handler          = "rag_ingest_worker.lambda_handler"
  runtime          = "python3.12"
  timeout          = 300
  memory_size      = 1024
  environment {
    variables = {
      VECTOR_BUCKET      = aws_s3_bucket.vectors.id
      INDEX_NAME         = var.vector_index_name
      SAGEMAKER_ENDPOINT = var.sagemaker_endpoint_name
    }
  }
  tags = { Project = "legal-companion", Part = "3" }
  depends_on = [aws_cloudwatch_log_group.rag_worker]
}

resource "aws_lambda_event_source_mapping" "rag_sqs" {
  event_source_arn = aws_sqs_queue.rag_ingest.arn
  function_name    = aws_lambda_function.rag_ingest_worker.arn
  batch_size       = 3
  function_response_types = ["ReportBatchItemFailures"]
}