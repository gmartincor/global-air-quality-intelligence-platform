variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "shard_count" {
  description = "Number of shards for Kinesis stream"
  type        = number
  default     = 1
}

variable "retention_hours" {
  description = "Retention period in hours"
  type        = number
  default     = 24
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {}
}
