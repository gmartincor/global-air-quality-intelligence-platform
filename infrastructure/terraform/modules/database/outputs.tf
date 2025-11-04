output "speed_layer_table_name" {
  description = "Name of the speed layer DynamoDB table"
  value       = aws_dynamodb_table.speed_layer.name
}

output "speed_layer_table_arn" {
  description = "ARN of the speed layer DynamoDB table"
  value       = aws_dynamodb_table.speed_layer.arn
}

output "dlq_table_name" {
  description = "Name of the DLQ DynamoDB table"
  value       = aws_dynamodb_table.dlq.name
}

output "dlq_table_arn" {
  description = "ARN of the DLQ DynamoDB table"
  value       = aws_dynamodb_table.dlq.arn
}
