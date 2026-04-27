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
# ECR Repository
# ========================================

# ECR repository for the researcher Docker image
resource "aws_ecr_repository" "researcher" {
  name                 = "legal-companion-researcher"
  image_tag_mutability = "MUTABLE"
  force_delete         = true  # Allow deletion even with images
  
  image_scanning_configuration {
    scan_on_push = false
  }
  
  tags = {
    Project = "legal-companion"
    Part    = "4"
  }
}

# ========================================
# App Runner Service
# ========================================

# IAM role for App Runner
resource "aws_iam_role" "app_runner_role" {
  name = "legal-companion-app-runner-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      },
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
  
  tags = {
    Project = "legal-companion"
    Part    = "4"
  }
}

# Policy for App Runner to access ECR
resource "aws_iam_role_policy_attachment" "app_runner_ecr_access" {
  role       = aws_iam_role.app_runner_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# IAM role for App Runner instance (runtime access to AWS services)
resource "aws_iam_role" "app_runner_instance_role" {
  name = "legal-companion-app-runner-instance-role"
  
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
  
  tags = {
    Project = "legal-companion"
    Part    = "4"
  }
}

# Policy for App Runner instance to access Bedrock
resource "aws_iam_role_policy" "app_runner_instance_bedrock_access" {
  name = "legal-companion-app-runner-instance-bedrock-policy"
  role = aws_iam_role.app_runner_instance_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
          "bedrock:ListFoundationModels"
        ]
        Resource = "*"
      }
    ]
  })
}

# App Runner service
resource "aws_apprunner_service" "researcher" {
  service_name = "legal-companion-researcher"
  
  source_configuration {
    auto_deployments_enabled = false
    
    # Configure authentication for private ECR repository
    authentication_configuration {
      access_role_arn = aws_iam_role.app_runner_role.arn
    }
    
    image_repository {
      image_identifier      = "${aws_ecr_repository.researcher.repository_url}:latest"
      image_configuration {
        port = "8000"
        runtime_environment_variables = {
          OPENAI_API_KEY     = var.openai_api_key
          LEGAL_API_ENDPOINT  = var.legal_api_endpoint
          LEGAL_API_KEY       = var.legal_api_key
          OPENROUTER_API_KEY  = var.openrouter_api_key
          OPENAI_CHAT_MODEL   = var.openai_chat_model
          SERPER_API_KEY      = var.serper_api_key
        }
      }
      image_repository_type = "ECR"
    }
  }
  
  instance_configuration {
    cpu    = "1 vCPU"
    memory = "2 GB"
    instance_role_arn = aws_iam_role.app_runner_instance_role.arn
  }
  
  tags = {
    Project = "legal-companion"
    Part    = "4"
  }
}
