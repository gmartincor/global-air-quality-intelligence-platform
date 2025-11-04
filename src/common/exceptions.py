from typing import Any, Optional


class AirQualityException(Exception):
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}

    def __str__(self) -> str:
        parts = [f"[{self.error_code}] {self.message}"]
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            parts.append(f"Context: {context_str}")
        return " | ".join(parts)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, error_code={self.error_code!r}, context={self.context!r})"


class ConfigurationError(AirQualityException):
    pass


class AWSClientError(AirQualityException):
    pass


class DataValidationError(AirQualityException):
    pass


class DataIngestionError(AirQualityException):
    pass


class DataProcessingError(AirQualityException):
    pass


class DataQualityError(AirQualityException):
    pass


class InfrastructureError(AirQualityException):
    pass


class OrchestrationError(AirQualityException):
    pass
