from unittest.mock import MagicMock, patch

import pytest
import boto3

from src.common.aws.client_factory import AWSClientFactory


class TestAWSClientFactory:
    @patch("src.common.aws.client_factory.boto3.client")
    @patch("src.common.aws.client_factory.config")
    def test_create_s3_client(self, mock_config: MagicMock, mock_boto3_client: MagicMock) -> None:
        mock_config.aws.endpoint_url = "http://localhost:4566"
        mock_config.aws.region = "us-east-1"
        mock_config.aws.access_key_id = "test"
        mock_config.aws.secret_access_key = "test"
        
        mock_s3_client = MagicMock()
        mock_boto3_client.return_value = mock_s3_client
        
        client = AWSClientFactory.create_s3_client()
        
        mock_boto3_client.assert_called_once_with(
            "s3",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1"
        )
        assert client == mock_s3_client

    @patch("src.common.aws.client_factory.boto3.client")
    @patch("src.common.aws.client_factory.config")
    def test_create_kinesis_client(self, mock_config: MagicMock, mock_boto3_client: MagicMock) -> None:
        mock_config.aws.endpoint_url = "http://localhost:4566"
        mock_config.aws.region = "us-east-1"
        mock_config.aws.access_key_id = "test"
        mock_config.aws.secret_access_key = "test"
        
        mock_kinesis_client = MagicMock()
        mock_boto3_client.return_value = mock_kinesis_client
        
        client = AWSClientFactory.create_kinesis_client()
        
        mock_boto3_client.assert_called_once_with(
            "kinesis",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1"
        )
        assert client == mock_kinesis_client

    @patch("src.common.aws.client_factory.boto3.client")
    @patch("src.common.aws.client_factory.config")
    def test_create_dynamodb_client(self, mock_config: MagicMock, mock_boto3_client: MagicMock) -> None:
        mock_config.aws.endpoint_url = "http://localhost:4566"
        mock_config.aws.region = "us-east-1"
        mock_config.aws.access_key_id = "test"
        mock_config.aws.secret_access_key = "test"
        
        mock_dynamodb_client = MagicMock()
        mock_boto3_client.return_value = mock_dynamodb_client
        
        client = AWSClientFactory.create_dynamodb_client()
        
        mock_boto3_client.assert_called_once_with(
            "dynamodb",
            endpoint_url="http://localhost:4566",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1"
        )
        assert client == mock_dynamodb_client
