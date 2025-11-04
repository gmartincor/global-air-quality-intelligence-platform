import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class LoggerManager:
    _loggers: dict[str, logging.Logger] = {}

    @classmethod
    def setup_logger(
        cls,
        name: str,
        level: int = logging.INFO,
        log_file: Optional[Path] = None,
        max_bytes: int = 10485760,
        backup_count: int = 5,
    ) -> logging.Logger:
        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False

        if logger.handlers:
            return logger

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(level)
            logger.addHandler(file_handler)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def get_logger(cls, name: str, level: Optional[int] = None) -> logging.Logger:
        if name in cls._loggers:
            logger = cls._loggers[name]
            if level is not None:
                logger.setLevel(level)
            return logger

        return cls.setup_logger(name, level=level or logging.INFO)


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    max_bytes: int = 10485760,
    backup_count: int = 5,
) -> logging.Logger:
    return LoggerManager.setup_logger(name, level, log_file, max_bytes, backup_count)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    return LoggerManager.get_logger(name, level)
