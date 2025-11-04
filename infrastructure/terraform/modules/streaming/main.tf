resource "aws_kinesis_stream" "measurements" {
  name             = "${var.project_name}-measurements"
  shard_count      = var.shard_count
  retention_period = var.retention_hours

  shard_level_metrics = [
    "IncomingBytes",
    "IncomingRecords",
    "OutgoingBytes",
    "OutgoingRecords",
    "WriteProvisionedThroughputExceeded",
    "ReadProvisionedThroughputExceeded",
  ]

  stream_mode_details {
    stream_mode = "PROVISIONED"
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-measurements"
      Description = "Real-time air quality measurements stream"
    }
  )
}
