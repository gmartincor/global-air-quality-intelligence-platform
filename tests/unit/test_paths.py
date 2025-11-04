import pytest
from pathlib import Path

from src.common.utils.paths import (
    get_project_root,
    get_config_dir,
    get_src_dir,
    get_tests_dir,
    get_logs_dir,
    get_data_dir,
    get_temp_dir,
    ensure_directory,
    safe_join,
    get_log_file,
)


class TestPathUtilities:
    def test_get_project_root(self):
        root = get_project_root()
        assert root.exists()
        assert root.is_dir()
        assert (root / "pyproject.toml").exists()

    def test_get_config_dir(self):
        config_dir = get_config_dir()
        assert config_dir == get_project_root() / "config"

    def test_get_src_dir(self):
        src_dir = get_src_dir()
        assert src_dir == get_project_root() / "src"
        assert src_dir.exists()

    def test_get_tests_dir(self):
        tests_dir = get_tests_dir()
        assert tests_dir == get_project_root() / "tests"
        assert tests_dir.exists()

    def test_get_logs_dir(self):
        logs_dir = get_logs_dir()
        assert logs_dir.exists()
        assert logs_dir.is_dir()

    def test_get_data_dir(self):
        data_dir = get_data_dir()
        assert data_dir.exists()
        assert data_dir.is_dir()

    def test_get_temp_dir(self):
        temp_dir = get_temp_dir()
        assert temp_dir.exists()
        assert temp_dir.is_dir()

    def test_ensure_directory(self, tmp_path):
        new_dir = tmp_path / "test" / "nested" / "dir"
        result = ensure_directory(new_dir)
        assert result.exists()
        assert result.is_dir()

    def test_safe_join(self):
        result = safe_join("base", "sub", "file.txt")
        assert result == Path("base/sub/file.txt")

    def test_safe_join_with_leading_slashes(self):
        result = safe_join("base", "/sub", "/file.txt")
        assert result == Path("base/sub/file.txt")

    def test_get_log_file(self):
        log_file = get_log_file("test_module")
        assert log_file.parent.exists()
        assert log_file.name == "test_module.log"
