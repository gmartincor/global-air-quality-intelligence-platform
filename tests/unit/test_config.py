from pathlib import Path

import pytest
import yaml

from src.common.config import (
    AWSConfig,
    AirflowConfig,
    AppConfig,
    DynamoDBConfig,
    KinesisConfig,
    PostgresConfig,
    RedisConfig,
    S3Config,
    SparkConfig,
)
from src.common.exceptions import ConfigurationError


@pytest.fixture
def sample_config_data() -> dict:
    return {
        "environment": "dev",
        "aws": {
            "endpoint_url": "http://localhost:4566",
            "region": "us-east-1",
            "access_key_id": "test",
            "secret_access_key": "test",
        },
        "s3": {
            "bronze_bucket": "dev-air-quality-bronze",
            "silver_bucket": "dev-air-quality-silver",
            "gold_bucket": "dev-air-quality-gold",
        },
        "kinesis": {"stream_name": "air-quality-measurements", "shard_count": 1},
        "dynamodb": {
            "speed_layer_table": "air-quality-realtime",
            "dlq_table": "air-quality-dlq",
        },
        "postgres": {
            "host": "localhost",
            "port": 5432,
            "database": "airflow",
            "user": "airflow",
            "password": "airflow",
        },
        "redis": {"host": "localhost", "port": 6379, "db": 0},
        "airflow": {"dags_folder": "/opt/airflow/dags", "executor": "CeleryExecutor"},
        "spark": {
            "master_url": "spark://spark-master:7077",
            "app_name": "air-quality-processing",
        },
    }


@pytest.fixture
def config_file(tmp_path: Path, sample_config_data: dict) -> Path:
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config_data, f)
    return config_path


class TestAWSConfig:
    def test_default_values(self) -> None:
        config = AWSConfig()
        assert config.endpoint_url == "http://localhost:4566"
        assert config.region == "us-east-1"
        assert config.access_key_id == "test"
        assert config.secret_access_key == "test"

    def test_custom_values(self) -> None:
        config = AWSConfig(
            endpoint_url="http://custom:4566",
            region="eu-west-1",
            access_key_id="custom_key",
            secret_access_key="custom_secret",
        )
        assert config.endpoint_url == "http://custom:4566"
        assert config.region == "eu-west-1"

    def test_invalid_region(self) -> None:
        with pytest.raises(ValueError, match="Invalid AWS region"):
            AWSConfig(region="invalid-region")


class TestPostgresConfig:
    def test_connection_string(self) -> None:
        config = PostgresConfig(
            host="localhost", port=5432, database="testdb", user="testuser", password="testpass"
        )
        expected = "postgresql://testuser:testpass@localhost:5432/testdb"
        assert config.connection_string == expected

    def test_connection_params(self) -> None:
        config = PostgresConfig(
            host="localhost", port=5432, database="testdb", user="testuser", password="testpass"
        )
        params = config.connection_params
        assert params["host"] == "localhost"
        assert params["port"] == 5432
        assert params["database"] == "testdb"

    def test_invalid_port(self) -> None:
        with pytest.raises(ValueError, match="Invalid port number"):
            PostgresConfig(
                host="localhost", port=70000, database="testdb", user="testuser", password="testpass"
            )


class TestRedisConfig:
    def test_default_values(self) -> None:
        config = RedisConfig(host="localhost")
        assert config.port == 6379
        assert config.db == 0

    def test_invalid_port(self) -> None:
        with pytest.raises(ValueError, match="Invalid port number"):
            RedisConfig(host="localhost", port=100000)

    def test_invalid_db(self) -> None:
        with pytest.raises(ValueError, match="Invalid Redis database number"):
            RedisConfig(host="localhost", db=20)


class TestAppConfig:
    def test_from_yaml(self, config_file: Path) -> None:
        config = AppConfig.from_yaml(config_file)

        assert config.environment == "dev"
        assert config.aws.region == "us-east-1"
        assert config.s3.bronze_bucket == "dev-air-quality-bronze"
        assert config.kinesis.stream_name == "air-quality-measurements"
        assert config.dynamodb.speed_layer_table == "air-quality-realtime"
        assert config.postgres.database == "airflow"
        assert config.redis.port == 6379
        assert config.airflow.executor == "CeleryExecutor"
        assert config.spark.master_url == "spark://spark-master:7077"

    def test_missing_config_file(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nonexistent.yaml"
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            AppConfig.from_yaml(nonexistent)

    def test_empty_config_file(self, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.yaml"
        empty_file.touch()
        with pytest.raises(ConfigurationError, match="Configuration file is empty"):
            AppConfig.from_yaml(empty_file)

    def test_missing_required_sections(self, tmp_path: Path) -> None:
        incomplete_file = tmp_path / "incomplete.yaml"
        with open(incomplete_file, "w") as f:
            yaml.dump({"environment": "dev", "aws": {}}, f)

        with pytest.raises(ConfigurationError, match="Missing configuration sections"):
            AppConfig.from_yaml(incomplete_file)

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        invalid_file = tmp_path / "invalid.yaml"
        with open(invalid_file, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ConfigurationError, match="Failed to parse YAML"):
            AppConfig.from_yaml(invalid_file)

    def test_invalid_environment(self, config_file: Path, sample_config_data: dict) -> None:
        sample_config_data["environment"] = "invalid"
        invalid_config = config_file.parent / "invalid_env.yaml"
        with open(invalid_config, "w") as f:
            yaml.dump(sample_config_data, f)

        with pytest.raises(ConfigurationError, match="Invalid environment"):
            AppConfig.from_yaml(invalid_config)
