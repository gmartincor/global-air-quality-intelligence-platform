from functools import lru_cache
from pathlib import Path
from typing import Any, Final, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from src.common.exceptions import ConfigurationError

VALID_AWS_REGIONS: Final[frozenset[str]] = frozenset([
    "us-east-1",
    "us-east-2",
    "us-west-1",
    "us-west-2",
    "eu-west-1",
    "eu-central-1",
    "ap-southeast-1",
    "ap-northeast-1",
])

VALID_ENVIRONMENTS: Final[frozenset[str]] = frozenset(["dev", "test", "staging", "prod"])

MIN_PORT: Final[int] = 1
MAX_PORT: Final[int] = 65535
MIN_REDIS_DB: Final[int] = 0
MAX_REDIS_DB: Final[int] = 15
MIN_KINESIS_SHARDS: Final[int] = 1
MAX_KINESIS_SHARDS: Final[int] = 500


def validate_port(port: int) -> int:
    if not MIN_PORT <= port <= MAX_PORT:
        raise ValueError(f"Port must be between {MIN_PORT} and {MAX_PORT}, got {port}")
    return port


def validate_positive_int(value: int, field_name: str) -> int:
    if value < 1:
        raise ValueError(f"{field_name} must be positive, got {value}")
    return value


class AWSConfig(BaseSettings):
    endpoint_url: str = Field(default="http://localhost:4566")
    region: str = Field(default="us-east-1")
    access_key_id: str = Field(default="test")
    secret_access_key: str = Field(default="test")

    @field_validator("region")
    @classmethod
    def validate_region(cls, v: str) -> str:
        if v not in VALID_AWS_REGIONS:
            raise ValueError(
                f"Invalid AWS region '{v}'. Valid regions: {', '.join(sorted(VALID_AWS_REGIONS))}"
            )
        return v


class S3Config(BaseSettings):
    bronze_bucket: str
    silver_bucket: str
    gold_bucket: str

    @property
    def buckets(self) -> dict[str, str]:
        return {
            "bronze": self.bronze_bucket,
            "silver": self.silver_bucket,
            "gold": self.gold_bucket,
        }


class KinesisConfig(BaseSettings):
    stream_name: str
    shard_count: int = 1

    @field_validator("shard_count")
    @classmethod
    def validate_shard_count(cls, v: int) -> int:
        if not MIN_KINESIS_SHARDS <= v <= MAX_KINESIS_SHARDS:
            raise ValueError(
                f"Shard count must be between {MIN_KINESIS_SHARDS} and {MAX_KINESIS_SHARDS}, got {v}"
            )
        return v


class DynamoDBConfig(BaseSettings):
    speed_layer_table: str
    dlq_table: str

    @property
    def tables(self) -> dict[str, str]:
        return {
            "speed_layer": self.speed_layer_table,
            "dlq": self.dlq_table,
        }


class PostgresConfig(BaseSettings):
    host: str
    port: int = 5432
    database: str
    user: str
    password: str

    @field_validator("port")
    @classmethod
    def validate_port_number(cls, v: int) -> int:
        return validate_port(v)

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"

    @property
    def connection_params(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
        }


class RedisConfig(BaseSettings):
    host: str
    port: int = 6379
    db: int = 0

    @field_validator("port")
    @classmethod
    def validate_port_number(cls, v: int) -> int:
        return validate_port(v)

    @field_validator("db")
    @classmethod
    def validate_db_number(cls, v: int) -> int:
        if not MIN_REDIS_DB <= v <= MAX_REDIS_DB:
            raise ValueError(
                f"Redis database must be between {MIN_REDIS_DB} and {MAX_REDIS_DB}, got {v}"
            )
        return v

    @property
    def connection_string(self) -> str:
        return f"redis://{self.host}:{self.port}/{self.db}"


class AirflowConfig(BaseSettings):
    dags_folder: str
    executor: str = "CeleryExecutor"

    @field_validator("executor")
    @classmethod
    def validate_executor(cls, v: str) -> str:
        valid_executors = {"LocalExecutor", "CeleryExecutor", "KubernetesExecutor", "SequentialExecutor"}
        if v not in valid_executors:
            raise ValueError(
                f"Invalid Airflow executor '{v}'. Valid executors: {', '.join(sorted(valid_executors))}"
            )
        return v


class SparkConfig(BaseSettings):
    master_url: str
    app_name: str = "air-quality-processing"

    @field_validator("master_url")
    @classmethod
    def validate_master_url(cls, v: str) -> str:
        if not (v.startswith("spark://") or v == "local" or v.startswith("local[")):
            raise ValueError(
                f"Invalid Spark master URL '{v}'. Must start with 'spark://' or be 'local' or 'local[*]'"
            )
        return v


class AppConfig(BaseSettings):
    environment: str = "dev"
    aws: AWSConfig
    s3: S3Config
    kinesis: KinesisConfig
    dynamodb: DynamoDBConfig
    postgres: PostgresConfig
    redis: RedisConfig
    airflow: AirflowConfig
    spark: SparkConfig

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        if v not in VALID_ENVIRONMENTS:
            raise ValueError(
                f"Invalid environment '{v}'. Valid environments: {', '.join(sorted(VALID_ENVIRONMENTS))}"
            )
        return v

    @classmethod
    def from_yaml(cls, path: Path) -> "AppConfig":
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse YAML configuration: {e}")
        except IOError as e:
            raise ConfigurationError(f"Failed to read configuration file: {e}")

        if not data:
            raise ConfigurationError("Configuration file is empty")

        required_sections = ["aws", "s3", "kinesis", "dynamodb", "postgres", "redis", "airflow", "spark"]
        missing_sections = [section for section in required_sections if section not in data]
        if missing_sections:
            raise ConfigurationError(
                f"Missing required configuration sections: {', '.join(missing_sections)}"
            )

        try:
            return cls(
                environment=data.get("environment", "dev"),
                aws=AWSConfig(**data["aws"]),
                s3=S3Config(**data["s3"]),
                kinesis=KinesisConfig(**data["kinesis"]),
                dynamodb=DynamoDBConfig(**data["dynamodb"]),
                postgres=PostgresConfig(**data["postgres"]),
                redis=RedisConfig(**data["redis"]),
                airflow=AirflowConfig(**data["airflow"]),
                spark=SparkConfig(**data["spark"]),
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize configuration: {e}")


@lru_cache(maxsize=1)
def get_config(config_path: Optional[Path] = None) -> AppConfig:
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    return AppConfig.from_yaml(config_path)


config = get_config()
