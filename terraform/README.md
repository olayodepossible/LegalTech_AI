# Terraform Infrastructure

This directory contains Terraform configurations for the Legal Companion project.

## Structure

Each part of the course has its own independent Terraform directory:

- **`2_sagemaker/`** - SageMaker serverless endpoint for embeddings 
- **`3_ingestion/`** - S3 Vectors, Lambda, and API Gateway for document ingestion
- **`4_researcher/`** - App Runner service for AI researcher agent
- **`5_database/`** - Aurora Serverless v2 PostgreSQL with Data API
- **`6_agents/`** - Lambda functions for agent orchestra
- **`7_frontend/`** - API Lambda and frontend infrastructure


## Usage

For each part of the course:

```bash
# Navigate to the specific part's directory
cd terraform/2_sagemaker  # (or 3_ingestion, 4_researcher, etc.)

# Initialize Terraform (only needed once per directory)
terraform init

# Review what will be created
terraform plan

# Deploy the infrastructure
terraform apply

# When done with that part (optional)
terraform destroy
```

## Environment Variables

Some Terraform configurations require environment variables from your `.env` file:

- `OPENAI_API_KEY` - For the researcher agent 
- `LEGAL_API_ENDPOINT` - API Gateway endpoint 
- `LEGAL_API_KEY` - API key for ingestion 
- `AURORA_CLUSTER_ARN` - Aurora cluster ARN 
- `AURORA_SECRET_ARN` - Secrets Manager ARN 
- `VECTOR_BUCKET` - S3 Vectors bucket name


## State Management

- Each directory maintains its own `terraform.tfstate` file
- State files are stored locally (not in S3)
- All `*.tfstate` files are gitignored for security
- Back up state files before making major changes


## Troubleshooting

If you encounter issues:

1. **State Conflicts**: Each directory has independent state. If you need to import existing resources:
   ```bash
   terraform import <resource_type>.<resource_name> <resource_id>
   ```

2. **Missing Dependencies**: Ensure you've completed earlier guides and have the required environment variables

3. **Clean Slate**: To start over in any directory:
   ```bash
   terraform destroy  # Remove resources
   rm -rf .terraform terraform.tfstate*  # Clean local files
   terraform init  # Reinitialize
   ```

## Cleanup Helper

To clean up old monolithic Terraform files (if upgrading from an older version):

```bash
cd terraform
python cleanup_old_structure.py
```

This will identify old files that can be safely removed.