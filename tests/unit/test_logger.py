import logging
from pathlib import Path

import pytest

from src.common.logger import get_logger, setup_logger


class TestLogger:
    def test_setup_logger_basic(self) -> None:
        logger = setup_logger("test_logger", level=logging.INFO)
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) >= 1

    def test_setup_logger_with_file(self, tmp_path: Path) -> None:
        log_file = tmp_path / "test.log"
        logger = setup_logger("test_file_logger", log_file=log_file)
        
        logger.info("Test message")
        
        assert log_file.exists()
        assert "Test message" in log_file.read_text()

    def test_get_logger(self) -> None:
        logger_name = "test_get_logger"
        logger = get_logger(logger_name)
        assert logger.name == logger_name

    def test_logger_no_duplicate_handlers(self) -> None:
        logger1 = setup_logger("duplicate_test")
        handler_count = len(logger1.handlers)
        
        logger2 = setup_logger("duplicate_test")
        
        assert len(logger2.handlers) == handler_count
