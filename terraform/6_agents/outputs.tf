output "sqs_queue_url" {
  description = "URL of the SQS queue for job submission"
  value       = aws_sqs_queue.analysis_jobs.url
}

output "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.analysis_jobs.arn
}

output "setup_instructions" {
  description = "Instructions for testing the agents"
  value = <<-EOT
    
    ✅ Agent infrastructure deployed successfully!
    
    SQS Queue: ${aws_sqs_queue.analysis_jobs.name}
  EOT
}