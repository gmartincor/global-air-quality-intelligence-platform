import pytest

from src.common.utils.string_utils import (
    to_snake_case,
    to_camel_case,
    to_pascal_case,
    to_kebab_case,
    truncate,
    normalize_whitespace,
    remove_special_chars,
    hash_string,
    generate_id,
    sanitize_filename,
    is_valid_email,
    mask_sensitive,
)


class TestStringUtilities:
    def test_to_snake_case(self):
        assert to_snake_case("HelloWorld") == "hello_world"
        assert to_snake_case("helloWorld") == "hello_world"
        assert to_snake_case("hello_world") == "hello_world"

    def test_to_camel_case(self):
        assert to_camel_case("hello_world") == "helloWorld"
        assert to_camel_case("hello_world_test") == "helloWorldTest"

    def test_to_pascal_case(self):
        assert to_pascal_case("hello_world") == "HelloWorld"
        assert to_pascal_case("hello_world_test") == "HelloWorldTest"

    def test_to_kebab_case(self):
        assert to_kebab_case("HelloWorld") == "hello-world"
        assert to_kebab_case("hello_world") == "hello-world"

    def test_truncate(self):
        assert truncate("Hello World", 5) == "He..."
        assert truncate("Hi", 10) == "Hi"

    def test_truncate_custom_suffix(self):
        assert truncate("Hello World", 8, suffix=">>") == "Hello >>>"

    def test_normalize_whitespace(self):
        assert normalize_whitespace("  hello   world  ") == "hello world"
        assert normalize_whitespace("hello\n\nworld") == "hello world"

    def test_remove_special_chars(self):
        assert remove_special_chars("hello@world!") == "helloworld"
        assert remove_special_chars("hello_world", keep="_") == "hello_world"

    def test_hash_string(self):
        result = hash_string("test")
        assert isinstance(result, str)
        assert len(result) == 64

    def test_hash_string_md5(self):
        result = hash_string("test", algorithm="md5")
        assert isinstance(result, str)
        assert len(result) == 32

    def test_generate_id(self):
        result = generate_id("test", length=10)
        assert len(result) == 10

    def test_sanitize_filename(self):
        assert sanitize_filename('test<file>name.txt') == "test_file_name.txt"
        assert sanitize_filename('test/file\\name') == "test_file_name"

    def test_is_valid_email(self):
        assert is_valid_email("test@example.com")
        assert is_valid_email("user.name@domain.co.uk")
        assert not is_valid_email("invalid.email")
        assert not is_valid_email("@example.com")

    def test_mask_sensitive(self):
        assert mask_sensitive("password123", visible_chars=4) == "pass*******"
        assert mask_sensitive("abc", visible_chars=4) == "***"
