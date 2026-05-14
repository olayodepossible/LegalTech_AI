# AI Agent Orchestra

In this guide, you'll deploy a sophisticated multi-agent AI system where specialized agents collaborate to provide comprehensive financial analysis.

## Prerequisites

Before starting, ensure you have:

- Completed Guides 1-5 (all infrastructure deployed)
- AWS CLI configured
- Python with `uv` package manager installed
- Docker Desktop running

## Step 1: Package Lambda Functions

Now let's create deployment packages for AWS Lambda. Each agent needs its dependencies packaged correctly for the Lambda environment.

### 4.1 Package All Agents

**In directory**: `backend`

```bash
uv run package_docker.py
```

This script:

1. Uses Docker to ensure Linux compatibility
2. Packages each agent with its dependencies
3. Creates zip files for Lambda deployment
4. Takes 2-3 minutes total

**Expected output**: 

```
Packaging tagger...
✅ Created tagger_lambda.zip (52 MB)
Packaging reporter...
✅ Created reporter_lambda.zip (68 MB)
Packaging charter...
✅ Created charter_lambda.zip (54 MB)
Packaging retirement...
✅ Created retirement_lambda.zip (55 MB)
Packaging planner...
✅ Created planner_lambda.zip (72 MB)
All agents packaged successfully!
```

## Step 2: Configure Terraform

Now let's set up the infrastructure configuration.

### 2.1 Set Terraform Variables

**In directory**: `terraform/6_agents`

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` in Cursor and update with your values:

```hcl
# Your AWS region for Lambda functions (should match your database region)
aws_region = "us-east-1"

# Aurora cluster ARN from Part 5 - populate with the ARN from Part 5  
aurora_cluster_arn = ""

# Aurora secret ARN from Part 5 - populate with the secret from Part 5  
aurora_secret_arn = ""

# S3 Vectors bucket name from Part 3
vector_bucket = "legal-vectors-123456789012"  # Replace with your account ID

# SageMaker endpoint name from Part 2
sagemaker_endpoint = "alex-embedding-endpoint"

```

## Step 3: Deploy Infrastructure

Let's deploy all five Lambda functions and supporting infrastructure.

### 6.1 Initialize Terraform

**In directory**: `terraform/6_agents`

```bash
terraform init
```

### 3.2 Review the Plan

```bash
terraform plan
```

Review what will be created:

- 5 Lambda functions with different memory/timeout settings
- S3 bucket for Lambda packages
- SQS queue with dead letter queue
- IAM roles and policies
- CloudWatch log groups

### 3.3 Deploy

```bash
terraform apply
```

Type `yes` when prompted. This takes 3-5 minutes to complete.

**Expected output**:

```
Apply complete! Resources: 25 added, 0 changed, 0 destroyed.

Outputs:
lambda_functions = {
  "charter" = "alex-charter"
  "planner" = "alex-planner"
  "reporter" = "alex-reporter"
  "retirement" = "alex-retirement"
  "tagger" = "alex-tagger"
}
sqs_queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/alex-analysis-jobs"
```

## Step 4: Deploy Lambda Code Updates

The Terraform deployment created the Lambda functions, but now we need to update them with our latest code:

**In directory**: `backend`

```bash
uv run deploy_all_lambdas.py
```

This updates all five Lambda functions with your packaged code. Takes about 1 minute.

**Expected output**:

```
Updating alex-tagger... ✅
Updating alex-reporter... ✅
Updating alex-charter... ✅
Updating alex-retirement... ✅
Updating alex-planner... ✅
All Lambda functions updated successfully!
```

## Step 5: Test Deployed Agents

Now let's test each agent running in AWS Lambda.

### 8.1 Test Individual Agents

Test each agent in AWS (run 3 times each to ensure reliability):

**In directory**: `backend/tagger`

```bash
uv run test_full.py
```

**In directory**: `backend/reporter`

```bash
uv run test_full.py
```

**In directory**: `backend/charter`

```bash
uv run test_full.py
```

**In directory**: `backend/retirement`

```bash
uv run test_full.py
```

**In directory**: `backend/planner`

```bash
uv run test_full.py
```

Each test should complete successfully. The planner test takes longer (60-90 seconds) as it coordinates all agents.

### 5.2 Test Complete System via SQS

**In directory**: `backend`

```bash
uv run test_full.py
```

This sends a message to SQS, triggering the full analysis pipeline. You'll see:

1. Job created in database
2. Message sent to SQS
3. Planner picks up message
4. Agents process in parallel
5. Results stored in database
6. Job marked complete

Total time: 90-120 seconds.

## Step 6: Test Advanced Scenarios

### 6.1 Multiple Accounts Test

Test with a user having multiple investment accounts:

**In directory**: `backend`

```bash
uv run test_multiple_accounts.py
```

This creates a user with 3 accounts (401k, IRA, Taxable) and runs full analysis. The system should handle all accounts correctly.

### 6.2 Scale Test

Test with multiple users simultaneously:

**In directory**: `backend`

```bash
uv run test_scale.py
```

This creates 5 users with varying portfolio sizes and runs analysis for all concurrently. Shows the system can handle multiple requests.

## Step 7: Explore the Database

Let's check what our agents created in the database:

**In directory**: `backend`

```bash
uv run check_jobs.py
```

This shows recent analysis jobs with their status and results. You'll see:

- Job IDs and timestamps
- User information
- Status (pending, processing, completed)
- Result sizes for each agent's output

## Step 8: Explore AWS Console

Let's see your infrastructure in action:

### 8.1 View Lambda Functions

1. Go to [Lambda Console](https://console.aws.amazon.com/lambda)
2. You'll see 5 functions: `alex-planner`, `alex-tagger`, `alex-reporter`, `alex-charter`, `alex-retirement`
3. Click on `alex-planner`
4. Go to the **Monitor** tab
5. Click **View CloudWatch logs**
6. Click on the latest log stream
7. You'll see detailed execution logs showing agent reasoning

### 8.2 Check SQS Queue

1. Go to [SQS Console](https://console.aws.amazon.com/sqs)
2. Click on `alex-analysis-jobs`
3. Check **Monitoring** tab for message metrics
4. The **Messages available** should be 0 (all processed)
5. Check the dead letter queue `alex-analysis-jobs-dlq` (should be empty)

### 8.3 Monitor Costs

1. Go to [Cost Management Console](https://console.aws.amazon.com/cost-management)
2. Click **Cost Explorer**
3. Filter by service to see:
  - Lambda costs (minimal, pay per invocation)
  - Aurora costs (~$1-2/day when paused)
  - Bedrock costs (pay per token)
  - SQS costs (fractions of a cent)

Expected monthly cost for development: $30-50.

## Troubleshooting

### Agent Timeout Issues

If agents time out:

1. Check Lambda function timeout settings (should be 60s for agents, 300s for planner)
2. Verify Bedrock model access in us-west-2
3. Check CloudWatch logs for specific errors

### Database Connection Failed

If database errors occur:

1. Verify Aurora cluster is running (not paused)
2. Check DATABASE_CLUSTER_ARN in Lambda environment variables
3. Ensure Data API is enabled on the cluster

### SQS Message Not Processing

If messages stay in queue:

1. Check planner Lambda has SQS trigger enabled
2. Verify IAM permissions for SQS access
3. Check dead letter queue for failed messages

### Rate Limit Errors

If you see rate limit errors:

1. The agents automatically retry with exponential backoff
2. Consider spacing out requests
3. The Nova Pro model has high limits but can still be exceeded

### Wrong Model Errors

If you see model not found errors:

1. Verify Bedrock model access in us-west-2
2. Check BEDROCK_MODEL_ID environment variable
3. Ensure using `us.amazon.nova-pro-v1:0` format

### Empty Results

If agents return empty results:

1. Check the test data includes valid portfolio positions
2. Verify database has instrument data (run migrate.py if needed)
3. Review CloudWatch logs for agent reasoning

## Architecture Deep Dive

### Agent Communication Pattern

The agents use a sophisticated pattern for collaboration:

1. **Asynchronous Triggering**: SQS decouples request from processing
2. **Pre-processing**: Orchestrator handles data preparation
3. **Parallel Execution**: Agents work simultaneously when possible
4. **Isolated Writes**: Each agent writes to its own database field
5. **Atomic Completion**: Job marked complete only when all succeed

### Tool Usage Strategy

Each agent uses tools differently:

- **Tagger**: No tools (structured outputs only)
- **Reporter**: Tools for S3 Vectors access and database writes
- **Charter**: No tools (returns JSON directly)
- **Retirement**: Tools for database writes
- **Planner**: Tools for invoking other agents and finalizing

This design avoids the tools + structured outputs conflict in the OpenAI Agents SDK.

### Error Handling

The system handles errors gracefully:

- Automatic retries with exponential backoff for rate limits
- Dead letter queue for failed messages
- Detailed logging for debugging
- Database tracks error states

## Next Steps

Congratulations! You've deployed a sophisticated multi-agent AI system. Your agents are now ready to provide intelligent financial analysis.

Continue to [Guide 7](7_frontend.md) where you'll build the frontend application that users will interact with to manage their portfolios and request analysis from your AI agents.

## Summary

In this guide, you:

- ✅ Deployed 5 specialized AI agents
- ✅ Set up agent orchestration with SQS
- ✅ Tested local and remote execution
- ✅ Verified multi-user scalability
- ✅ Explored monitoring and cost management

Your AI orchestra is now ready to perform! 🎭