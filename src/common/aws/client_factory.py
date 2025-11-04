from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Callable, Iterator, TypeVar

import boto3
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from mypy_boto3_dynamodb import DynamoDBClient, DynamoDBServiceResource
from mypy_boto3_kinesis import KinesisClient
from mypy_boto3_s3 import S3Client

from src.common.config import config
from src.common.exceptions import AWSClientError
from src.common.logger import get_logger

logger = get_logger(__name__)

ClientType = TypeVar("ClientType", bound=BaseClient)


class AWSClientFactory:
    @classmethod
    @lru_cache(maxsize=1)
    def _get_session_config(cls) -> dict[str, Any]:
        return {
            "aws_access_key_id": config.aws.access_key_id,
            "aws_secret_access_key": config.aws.secret_access_key,
            "region_name": config.aws.region,
        }

    @classmethod
    def _create_client(
        cls,
        service_name: str,
        client_type: str = "client",
    ) -> Any:
        try:
            creator: Callable[..., Any] = getattr(boto3, client_type)
            return creator(
                service_name,
                endpoint_url=config.aws.endpoint_url,
                **cls._get_session_config(),
            )
        except (BotoCoreError, ClientError) as e:
            error_msg = f"Failed to create {service_name} {client_type}"
            logger.error(f"{error_msg}: {e}")
            raise AWSClientError(f"{error_msg}: {e}") from e
        except Exception as e:
            error_msg = f"Unexpected error creating {service_name} {client_type}"
            logger.error(f"{error_msg}: {e}")
            raise AWSClientError(f"{error_msg}: {e}") from e

    @classmethod
    def create_s3_client(cls) -> S3Client:
        return cls._create_client("s3")

    @classmethod
    def create_kinesis_client(cls) -> KinesisClient:
        return cls._create_client("kinesis")

    @classmethod
    def create_dynamodb_client(cls) -> DynamoDBClient:
        return cls._create_client("dynamodb")

    @classmethod
    def create_dynamodb_resource(cls) -> DynamoDBServiceResource:
        return cls._create_client("dynamodb", client_type="resource")

    @classmethod
    @contextmanager
    def _get_client_context(cls, create_func: Callable[[], ClientType]) -> Iterator[ClientType]:
        client = create_func()
        try:
            logger.debug(f"Created {client.__class__.__name__}")
            yield client
        except Exception as e:
            logger.error(f"Error using {client.__class__.__name__}: {e}")
            raise
        finally:
            if hasattr(client, "close"):
                client.close()
                logger.debug(f"Closed {client.__class__.__name__}")

    @classmethod
    @contextmanager
    def get_s3_client(cls) -> Iterator[S3Client]:
        with cls._get_client_context(cls.create_s3_client) as client:
            yield client

    @classmethod
    @contextmanager
    def get_kinesis_client(cls) -> Iterator[KinesisClient]:
        with cls._get_client_context(cls.create_kinesis_client) as client:
            yield client

    @classmethod
    @contextmanager
    def get_dynamodb_client(cls) -> Iterator[DynamoDBClient]:
        with cls._get_client_context(cls.create_dynamodb_client) as client:
            yield client

    @classmethod
    @contextmanager
    def get_dynamodb_resource(cls) -> Iterator[DynamoDBServiceResource]:
        with cls._get_client_context(cls.create_dynamodb_resource) as resource:
            yield resource
