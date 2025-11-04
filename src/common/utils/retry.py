import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Type

from src.common.logger import get_logger

logger = get_logger(__name__)


class BackoffStrategy(Enum):
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if delay < 0:
        raise ValueError("delay must be non-negative")
    if backoff < 1:
        raise ValueError("backoff must be at least 1")

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            current_delay = delay

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1

                    if on_retry:
                        on_retry(e, attempt)

                    if attempt >= max_attempts:
                        logger.error(
                            f"Function '{func.__name__}' failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"Function '{func.__name__}' failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )

                    time.sleep(current_delay)

                    if backoff_strategy == BackoffStrategy.EXPONENTIAL:
                        current_delay *= backoff
                    elif backoff_strategy == BackoffStrategy.LINEAR:
                        current_delay += delay
                    elif backoff_strategy == BackoffStrategy.CONSTANT:
                        current_delay = delay

            return None

        return wrapper

    return decorator
