from typing import Final

PROJECT_NAME: Final[str] = "global-air-quality"

DEFAULT_LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"

DEFAULT_RETRY_ATTEMPTS: Final[int] = 3
DEFAULT_RETRY_DELAY: Final[float] = 1.0
DEFAULT_RETRY_BACKOFF: Final[float] = 2.0

MAX_LOG_FILE_SIZE: Final[int] = 10485760
MAX_LOG_BACKUP_COUNT: Final[int] = 5

AWS_DEFAULT_REGION: Final[str] = "us-east-1"
AWS_LOCALSTACK_ENDPOINT: Final[str] = "http://localhost:4566"

S3_BRONZE_PREFIX: Final[str] = "bronze"
S3_SILVER_PREFIX: Final[str] = "silver"
S3_GOLD_PREFIX: Final[str] = "gold"

KINESIS_DEFAULT_SHARD_COUNT: Final[int] = 1
KINESIS_RETENTION_HOURS: Final[int] = 24

DYNAMODB_BILLING_MODE: Final[str] = "PAY_PER_REQUEST"
DYNAMODB_TTL_ATTRIBUTE: Final[str] = "ttl"

POSTGRES_DEFAULT_PORT: Final[int] = 5432
REDIS_DEFAULT_PORT: Final[int] = 6379

AIRFLOW_DEFAULT_EXECUTOR: Final[str] = "CeleryExecutor"
SPARK_DEFAULT_APP_NAME: Final[str] = "air-quality-processing"
