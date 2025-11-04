terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    s3       = var.localstack_endpoint
    kinesis  = var.localstack_endpoint
    dynamodb = var.localstack_endpoint
  }
}

locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

module "storage" {
  source       = "./modules/storage"
  environment  = var.environment
  project_name = var.project_name
  tags         = local.common_tags
}

module "streaming" {
  source       = "./modules/streaming"
  environment  = var.environment
  project_name = var.project_name
  shard_count  = var.kinesis_shard_count
  tags         = local.common_tags
}

module "database" {
  source       = "./modules/database"
  environment  = var.environment
  project_name = var.project_name
  tags         = local.common_tags
}
