resource "aws_s3_bucket" "bronze" {
  bucket = "${var.environment}-${var.project_name}-bronze"

  tags = merge(
    var.tags,
    {
      Name  = "${var.environment}-${var.project_name}-bronze"
      Layer = "bronze"
      Description = "Raw data storage layer - immutable, append-only"
    }
  )
}

resource "aws_s3_bucket_lifecycle_configuration" "bronze" {
  bucket = aws_s3_bucket.bronze.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 180
      storage_class = "GLACIER"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "bronze" {
  bucket = aws_s3_bucket.bronze.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "silver" {
  bucket = "${var.environment}-${var.project_name}-silver"

  tags = merge(
    var.tags,
    {
      Name  = "${var.environment}-${var.project_name}-silver"
      Layer = "silver"
      Description = "Cleaned and validated data with schema enforcement"
    }
  )
}

resource "aws_s3_bucket_versioning" "silver" {
  bucket = aws_s3_bucket.silver.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "silver" {
  bucket = aws_s3_bucket.silver.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket" "gold" {
  bucket = "${var.environment}-${var.project_name}-gold"

  tags = merge(
    var.tags,
    {
      Name  = "${var.environment}-${var.project_name}-gold"
      Layer = "gold"
      Description = "Business-ready aggregated data"
    }
  )
}

resource "aws_s3_bucket_server_side_encryption_configuration" "gold" {
  bucket = aws_s3_bucket.gold.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
