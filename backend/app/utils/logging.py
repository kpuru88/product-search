"""Logging utilities for the application."""


def log_info(message: str) -> None:
    """Log an informational message."""
    print(message)


def log_error(message: str) -> None:
    """Log an error message."""
    print(f"ERROR: {message}")


def log_warning(message: str) -> None:
    """Log a warning message."""
    print(f"WARNING: {message}")

