from pathlib import Path
from typing import Any, Optional, Union


class ValidationError(ValueError):
    pass


def validate_not_empty(value: Any, field_name: str) -> None:
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} cannot be empty")


def validate_positive(value: Union[int, float], field_name: str) -> None:
    if value <= 0:
        raise ValidationError(f"{field_name} must be positive, got {value}")


def validate_non_negative(value: Union[int, float], field_name: str) -> None:
    if value < 0:
        raise ValidationError(f"{field_name} must be non-negative, got {value}")


def validate_in_range(
    value: Union[int, float],
    min_val: Union[int, float],
    max_val: Union[int, float],
    field_name: str,
    inclusive: bool = True,
) -> None:
    if inclusive:
        if not min_val <= value <= max_val:
            raise ValidationError(f"{field_name} must be between {min_val} and {max_val}, got {value}")
    else:
        if not min_val < value < max_val:
            raise ValidationError(f"{field_name} must be strictly between {min_val} and {max_val}, got {value}")


def validate_type(value: Any, expected_type: type, field_name: str) -> None:
    if not isinstance(value, expected_type):
        raise ValidationError(
            f"{field_name} must be of type {expected_type.__name__}, got {type(value).__name__}"
        )


def validate_file_exists(path: Union[str, Path], field_name: Optional[str] = None) -> Path:
    file_path = Path(path) if isinstance(path, str) else path
    name = field_name or "File"
    if not file_path.exists():
        raise ValidationError(f"{name} does not exist: {file_path}")
    if not file_path.is_file():
        raise ValidationError(f"{name} is not a file: {file_path}")
    return file_path


def validate_directory_exists(path: Union[str, Path], field_name: Optional[str] = None) -> Path:
    dir_path = Path(path) if isinstance(path, str) else path
    name = field_name or "Directory"
    if not dir_path.exists():
        raise ValidationError(f"{name} does not exist: {dir_path}")
    if not dir_path.is_dir():
        raise ValidationError(f"{name} is not a directory: {dir_path}")
    return dir_path


def validate_string_length(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    field_name: str = "String",
) -> None:
    length = len(value)
    if min_length is not None and length < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters, got {length}")
    if max_length is not None and length > max_length:
        raise ValidationError(f"{field_name} must be at most {max_length} characters, got {length}")


def validate_in_set(
    value: Any,
    valid_values: set[Any],
    field_name: str,
) -> None:
    if value not in valid_values:
        raise ValidationError(
            f"{field_name} must be one of {sorted(valid_values)}, got {value}"
        )
