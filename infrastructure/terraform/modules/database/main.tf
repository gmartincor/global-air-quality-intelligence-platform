resource "aws_dynamodb_table" "speed_layer" {
  name         = "${var.project_name}-realtime"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "city_id"
  range_key    = "timestamp"

  attribute {
    name = "city_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = var.enable_point_in_time_recovery
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-realtime"
      Type = "speed-layer"
      Description = "Real-time air quality data with 24h TTL"
    }
  )
}

resource "aws_dynamodb_table" "dlq" {
  name         = "${var.project_name}-dlq"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "error_id"
  range_key    = "timestamp"

  attribute {
    name = "error_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  server_side_encryption {
    enabled = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-dlq"
      Type = "dead-letter-queue"
      Description = "Failed message storage for debugging and replay"
    }
  )
}
