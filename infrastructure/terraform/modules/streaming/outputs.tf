output "stream_name" {
  description = "Name of the Kinesis stream"
  value       = aws_kinesis_stream.measurements.name
}

output "stream_arn" {
  description = "ARN of the Kinesis stream"
  value       = aws_kinesis_stream.measurements.arn
}
