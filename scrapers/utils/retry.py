"""
Retry logic with exponential backoff for flaky operations
"""

import time
import logging
from typing import Callable, TypeVar, Optional
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Decorator for retrying functions with exponential backoff

    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiply delay by this factor each retry
        exceptions: Tuple of exceptions to catch
        on_retry: Optional callback called on each retry

    Example:
        @retry_with_backoff(max_attempts=3, exceptions=(TimeoutException,))
        def click_button(driver, selector):
            driver.find_element(By.CSS_SELECTOR, selector).click()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )

                    if on_retry:
                        on_retry(attempt, e)

                    time.sleep(delay)
                    delay *= backoff_factor

            # Should never reach here, but for type checker
            raise last_exception

        return wrapper
    return decorator


# Specialized decorators for common use cases
def retry_selenium_action(max_attempts: int = 3):
    """Retry decorator for Selenium actions"""
    from selenium.common.exceptions import (
        TimeoutException,
        StaleElementReferenceException,
        ElementClickInterceptedException
    )

    return retry_with_backoff(
        max_attempts=max_attempts,
        exceptions=(
            TimeoutException,
            StaleElementReferenceException,
            ElementClickInterceptedException
        )
    )


def retry_api_call(max_attempts: int = 3):
    """Retry decorator for API calls (timeouts and connection errors)"""
    import requests

    return retry_with_backoff(
        max_attempts=max_attempts,
        exceptions=(
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        )
    )


class RetryableHTTPError(Exception):
    """Raised for HTTP errors that should be retried (5xx server errors)"""
    pass


def retry_on_server_error(max_attempts: int = 3, initial_delay: float = 2.0):
    """
    Retry decorator for HTTP requests that may fail with 5xx server errors.

    Usage:
        @retry_on_server_error(max_attempts=3)
        def make_api_call():
            response = session.get(url)
            response.raise_for_status()
            return response.json()
    """
    import requests

    return retry_with_backoff(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff_factor=2.0,
        exceptions=(
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            RetryableHTTPError,
        )
    )