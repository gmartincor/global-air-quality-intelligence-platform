import pytest

from src.common.constants import (
    PROJECT_NAME,
    AWS_DEFAULT_REGION,
    AWS_LOCALSTACK_ENDPOINT,
    S3_BRONZE_PREFIX,
    S3_SILVER_PREFIX,
    S3_GOLD_PREFIX,
    KINESIS_DEFAULT_SHARD_COUNT,
    POSTGRES_DEFAULT_PORT,
    REDIS_DEFAULT_PORT,
)


class TestConstants:
    def test_project_name(self):
        assert PROJECT_NAME == "global-air-quality"

    def test_aws_constants(self):
        assert AWS_DEFAULT_REGION == "us-east-1"
        assert AWS_LOCALSTACK_ENDPOINT == "http://localhost:4566"

    def test_s3_prefixes(self):
        assert S3_BRONZE_PREFIX == "bronze"
        assert S3_SILVER_PREFIX == "silver"
        assert S3_GOLD_PREFIX == "gold"

    def test_default_ports(self):
        assert POSTGRES_DEFAULT_PORT == 5432
        assert REDIS_DEFAULT_PORT == 6379

    def test_kinesis_constants(self):
        assert KINESIS_DEFAULT_SHARD_COUNT == 1
