output "s3_buckets" {
  description = "S3 bucket names by layer"
  value       = module.storage.buckets
}

output "kinesis_stream_name" {
  description = "Kinesis stream name"
  value       = module.streaming.stream_name
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    speed_layer = module.database.speed_layer_table_name
    dlq         = module.database.dlq_table_name
  }
}
