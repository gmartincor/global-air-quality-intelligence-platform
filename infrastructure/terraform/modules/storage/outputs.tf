output "buckets" {
  description = "Map of bucket names by layer"
  value = {
    bronze = aws_s3_bucket.bronze.id
    silver = aws_s3_bucket.silver.id
    gold   = aws_s3_bucket.gold.id
  }
}

output "bronze_bucket_arn" {
  description = "ARN of the bronze bucket"
  value       = aws_s3_bucket.bronze.arn
}

output "silver_bucket_arn" {
  description = "ARN of the silver bucket"
  value       = aws_s3_bucket.silver.arn
}

output "gold_bucket_arn" {
  description = "ARN of the gold bucket"
  value       = aws_s3_bucket.gold.arn
}
