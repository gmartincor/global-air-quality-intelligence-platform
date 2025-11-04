import pytest

from src.common.utils.validators import validate_in_range, validate_not_empty, validate_positive


class TestValidators:
    def test_validate_not_empty_with_value(self) -> None:
        validate_not_empty("test", "field_name")

    def test_validate_not_empty_raises_on_empty_string(self) -> None:
        with pytest.raises(ValueError, match="field_name cannot be empty"):
            validate_not_empty("", "field_name")

    def test_validate_not_empty_raises_on_none(self) -> None:
        with pytest.raises(ValueError, match="field_name cannot be empty"):
            validate_not_empty(None, "field_name")

    def test_validate_positive_with_positive_int(self) -> None:
        validate_positive(10, "count")

    def test_validate_positive_with_positive_float(self) -> None:
        validate_positive(10.5, "value")

    def test_validate_positive_raises_on_zero(self) -> None:
        with pytest.raises(ValueError, match="count must be positive"):
            validate_positive(0, "count")

    def test_validate_positive_raises_on_negative(self) -> None:
        with pytest.raises(ValueError, match="count must be positive"):
            validate_positive(-5, "count")

    def test_validate_in_range_valid(self) -> None:
        validate_in_range(5, 0, 10, "value")

    def test_validate_in_range_at_min_boundary(self) -> None:
        validate_in_range(0, 0, 10, "value")

    def test_validate_in_range_at_max_boundary(self) -> None:
        validate_in_range(10, 0, 10, "value")

    def test_validate_in_range_below_min(self) -> None:
        with pytest.raises(ValueError, match="value must be between"):
            validate_in_range(-1, 0, 10, "value")

    def test_validate_in_range_above_max(self) -> None:
        with pytest.raises(ValueError, match="value must be between"):
            validate_in_range(11, 0, 10, "value")
