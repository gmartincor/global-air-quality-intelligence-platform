import hashlib
import re
from typing import Optional


def to_snake_case(text: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", text)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def to_camel_case(text: str) -> str:
    components = text.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def to_pascal_case(text: str) -> str:
    return "".join(x.title() for x in text.split("_"))


def to_kebab_case(text: str) -> str:
    return to_snake_case(text).replace("_", "-")


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def remove_special_chars(text: str, keep: Optional[str] = None) -> str:
    if keep is None:
        keep = ""
    pattern = f"[^a-zA-Z0-9{re.escape(keep)}]"
    return re.sub(pattern, "", text)


def hash_string(text: str, algorithm: str = "sha256") -> str:
    hash_func = getattr(hashlib, algorithm)
    return hash_func(text.encode()).hexdigest()


def generate_id(text: str, length: int = 16) -> str:
    full_hash = hash_string(text)
    return full_hash[:length]


def sanitize_filename(filename: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    sanitized = re.sub(r"_+", "_", sanitized)
    return sanitized.strip("_")


def is_valid_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def mask_sensitive(text: str, visible_chars: int = 4) -> str:
    if len(text) <= visible_chars:
        return "*" * len(text)
    return text[:visible_chars] + "*" * (len(text) - visible_chars)
