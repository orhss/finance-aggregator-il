"""
Error handling utilities for Streamlit UI.

Provides safe wrappers for service calls with user-friendly error messages.
"""

import streamlit as st
import traceback
from typing import Any, Callable, Optional, TypeVar
from functools import wraps
import logging

# Set up logger
logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_service_call(
    func: Callable[..., T],
    *args,
    error_message: Optional[str] = None,
    show_error: bool = True,
    default_return: Any = None,
    **kwargs
) -> Optional[T]:
    """
    Wrapper for service calls with error handling.

    Args:
        func: Function to call
        *args: Positional arguments for func
        error_message: Custom error message to display (optional)
        show_error: Whether to show error in UI (default: True)
        default_return: Value to return on error (default: None)
        **kwargs: Keyword arguments for func

    Returns:
        Function result or default_return on error

    Example:
        result = safe_service_call(
            analytics_service.get_spending_by_category,
            start_date=start,
            end_date=end,
            error_message="Failed to load spending data"
        )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        # Log the full error
        logger.error(f"Error in {func.__name__}: {str(e)}")
        logger.debug(traceback.format_exc())

        # Show user-friendly error
        if show_error:
            if error_message:
                st.error(f"{error_message}: {get_user_friendly_error(e)}")
            else:
                st.error(f"An error occurred: {get_user_friendly_error(e)}")

        return default_return


def get_user_friendly_error(error: Exception) -> str:
    """
    Convert technical error to user-friendly message.

    Args:
        error: The exception that occurred

    Returns:
        User-friendly error message
    """
    error_str = str(error)
    error_type = type(error).__name__

    # Database errors
    if "database" in error_str.lower() or "sql" in error_str.lower():
        return "Database connection issue. Please try refreshing the page."

    # File not found
    if "FileNotFoundError" in error_type or "not found" in error_str.lower():
        return "Required file or data not found. Please ensure the database is initialized."

    # Permission errors
    if "PermissionError" in error_type or "permission" in error_str.lower():
        return "Permission denied. Please check file access permissions."

    # Network/connection errors
    if "connection" in error_str.lower() or "timeout" in error_str.lower():
        return "Connection issue. Please check your internet connection and try again."

    # Credential errors
    if "credential" in error_str.lower() or "authentication" in error_str.lower():
        return "Credential issue. Please check your configuration."

    # Value errors (often from invalid input)
    if "ValueError" in error_type:
        return f"Invalid input: {error_str}"

    # Generic fallback
    return f"{error_type}: {error_str}"


def safe_call_with_spinner(
    func: Callable[..., T],
    spinner_text: str = "Loading...",
    error_message: Optional[str] = None,
    default_return: Any = None,
    *args,
    **kwargs
) -> Optional[T]:
    """
    Wrapper that combines spinner and error handling.

    Args:
        func: Function to call
        spinner_text: Text to show in spinner
        error_message: Custom error message (optional)
        default_return: Value to return on error
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Function result or default_return on error

    Example:
        data = safe_call_with_spinner(
            get_transactions_cached,
            spinner_text="Loading transactions...",
            error_message="Failed to load transactions",
            start_date=start,
            end_date=end
        )
    """
    with st.spinner(spinner_text):
        return safe_service_call(
            func,
            *args,
            error_message=error_message,
            show_error=True,
            default_return=default_return,
            **kwargs
        )


def handle_error_with_retry(
    func: Callable[..., T],
    retry_button_text: str = "Retry",
    error_message: Optional[str] = None,
    *args,
    **kwargs
) -> Optional[T]:
    """
    Error handler that provides a retry button on failure.

    Args:
        func: Function to call
        retry_button_text: Text for retry button
        error_message: Custom error message
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func

    Returns:
        Function result or None on error

    Example:
        data = handle_error_with_retry(
            load_dashboard_data,
            retry_button_text="Reload Dashboard",
            error_message="Failed to load dashboard"
        )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in {func.__name__}: {str(e)}")
        logger.debug(traceback.format_exc())

        # Show error with retry button
        col1, col2 = st.columns([4, 1])
        with col1:
            if error_message:
                st.error(f"{error_message}: {get_user_friendly_error(e)}")
            else:
                st.error(f"An error occurred: {get_user_friendly_error(e)}")
        with col2:
            if st.button(retry_button_text, key=f"retry_{func.__name__}"):
                st.rerun()

        return None


def safe_decorator(
    error_message: Optional[str] = None,
    show_error: bool = True,
    default_return: Any = None
):
    """
    Decorator for making functions safe with error handling.

    Args:
        error_message: Custom error message
        show_error: Whether to show error in UI
        default_return: Value to return on error

    Example:
        @safe_decorator(error_message="Failed to load data")
        def load_data():
            # ... code that might raise exception
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Optional[T]]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[T]:
            return safe_service_call(
                func,
                *args,
                error_message=error_message,
                show_error=show_error,
                default_return=default_return,
                **kwargs
            )
        return wrapper
    return decorator


class ErrorBoundary:
    """
    Context manager for error handling in page sections.

    Example:
        with ErrorBoundary("Failed to load transactions"):
            # Code that might fail
            transactions = load_transactions()
            display_table(transactions)
    """

    def __init__(
        self,
        error_message: str = "An error occurred",
        show_traceback: bool = False
    ):
        self.error_message = error_message
        self.show_traceback = show_traceback

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, _exc_tb):
        if exc_type is not None:
            logger.error(f"Error in ErrorBoundary: {str(exc_val)}")
            if self.show_traceback:
                logger.debug(traceback.format_exc())

            st.error(f"{self.error_message}: {get_user_friendly_error(exc_val)}")

            # Return True to suppress the exception
            return True


def validate_date_range(start_date: Any, end_date: Any) -> bool:
    """
    Validate date range inputs.

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        True if valid, False otherwise (shows error message)
    """
    if not start_date or not end_date:
        st.error("Please select both start and end dates.")
        return False

    if start_date > end_date:
        st.error("Start date must be before end date.")
        return False

    return True


def validate_required_field(value: Any, field_name: str) -> bool:
    """
    Validate that a required field has a value.

    Args:
        value: Field value
        field_name: Name of the field (for error message)

    Returns:
        True if valid, False otherwise (shows error message)
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        st.error(f"{field_name} is required.")
        return False

    return True


def show_warning(message: str, icon: str = "⚠️"):
    """
    Show a warning message with icon.

    Args:
        message: Warning message
        icon: Icon to show (default: ⚠️)
    """
    st.warning(f"{icon} {message}")


def show_success(message: str, icon: str = "✅"):
    """
    Show a success message with icon.

    Args:
        message: Success message
        icon: Icon to show (default: ✅)
    """
    st.success(f"{icon} {message}")


def show_info(message: str, icon: str = "ℹ️"):
    """
    Show an info message with icon.

    Args:
        message: Info message
        icon: Icon to show (default: ℹ️)
    """
    st.info(f"{icon} {message}")
