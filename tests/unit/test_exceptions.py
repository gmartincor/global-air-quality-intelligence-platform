import pytest

from src.common.exceptions import (
    AWSClientError,
    AirQualityException,
    ConfigurationError,
    DataIngestionError,
    DataProcessingError,
    DataQualityError,
    DataValidationError,
)


class TestExceptions:
    def test_base_exception(self) -> None:
        exc = AirQualityException("Test message")
        assert str(exc) == "Test message"
        assert isinstance(exc, Exception)

    def test_configuration_error(self) -> None:
        exc = ConfigurationError("Config error")
        assert isinstance(exc, AirQualityException)
        assert str(exc) == "Config error"

    def test_aws_client_error(self) -> None:
        exc = AWSClientError("AWS error")
        assert isinstance(exc, AirQualityException)

    def test_data_validation_error(self) -> None:
        exc = DataValidationError("Validation failed")
        assert isinstance(exc, AirQualityException)

    def test_data_ingestion_error(self) -> None:
        exc = DataIngestionError("Ingestion failed")
        assert isinstance(exc, AirQualityException)

    def test_data_processing_error(self) -> None:
        exc = DataProcessingError("Processing failed")
        assert isinstance(exc, AirQualityException)

    def test_data_quality_error(self) -> None:
        exc = DataQualityError("Quality check failed")
        assert isinstance(exc, AirQualityException)
