from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent.parent


def get_config_dir() -> Path:
    return get_project_root() / "config"


def get_src_dir() -> Path:
    return get_project_root() / "src"


def get_tests_dir() -> Path:
    return get_project_root() / "tests"


def get_logs_dir() -> Path:
    logs_dir = get_project_root() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_data_dir() -> Path:
    data_dir = get_project_root() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_temp_dir() -> Path:
    temp_dir = get_project_root() / "tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_join(*parts: str) -> Path:
    result = Path(parts[0])
    for part in parts[1:]:
        clean_part = part.lstrip("/").lstrip("\\")
        result = result / clean_part
    return result


def get_log_file(module_name: str, create_dirs: bool = True) -> Path:
    log_file = get_logs_dir() / f"{module_name}.log"
    if create_dirs:
        log_file.parent.mkdir(parents=True, exist_ok=True)
    return log_file
