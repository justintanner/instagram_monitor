"""Logging utilities for Instagram monitor."""

import os
import platform
import sys
from typing import List, Optional

import requests


class Logger:
    """Dual output logger that writes to both stdout and a log file."""

    def __init__(self, filename: str):
        """Initialize logger with output file.

        Args:
            filename: Path to log file
        """
        self.terminal = sys.stdout
        self.logfile = open(filename, "a", buffering=1, encoding="utf-8")
        self.last_output: List[str] = []

    def write(self, message: str) -> None:
        """Write message to both terminal and log file.

        Args:
            message: Message to write
        """
        if message != "\n":
            self.last_output.append(message)
        self.terminal.write(message)
        self.logfile.write(message)
        self.terminal.flush()
        self.logfile.flush()

    def flush(self) -> None:
        """Flush output streams."""
        self.terminal.flush()
        self.logfile.flush()

    def close(self) -> None:
        """Close the log file."""
        self.logfile.close()

    def get_last_output(self) -> List[str]:
        """Get list of recent output messages."""
        return self.last_output

    def clear_last_output(self) -> None:
        """Clear the last output buffer."""
        self.last_output = []


def check_internet(url: str = "https://www.instagram.com/", timeout: int = 5, user_agent: str = "") -> bool:
    """Check internet connectivity by making a request.

    Args:
        url: URL to check connectivity against
        timeout: Request timeout in seconds
        user_agent: User agent string for the request

    Returns:
        True if connection successful, False otherwise
    """
    try:
        headers = {"User-Agent": user_agent} if user_agent else {}
        requests.get(url, headers=headers, timeout=timeout)
        return True
    except requests.RequestException as e:
        print(f"* No connectivity, please check your network:\n\n{e}")
        return False


def clear_screen(enabled: bool = True) -> None:
    """Clear the terminal screen.

    Args:
        enabled: If False, do nothing
    """
    if not enabled:
        return
    try:
        if platform.system() == "Windows":
            os.system("cls")
        else:
            os.system("clear")
    except Exception:
        print("* Cannot clear the screen contents")


def resolve_executable(executable: str) -> Optional[str]:
    """Resolve an executable path, searching PATH if needed.

    Args:
        executable: Executable name or path

    Returns:
        Full path to executable if found, None otherwise
    """
    if not executable:
        return None

    # Check if it's already an absolute path
    if os.path.isabs(executable) and os.path.isfile(executable):
        return executable

    # Search in PATH
    import shutil

    return shutil.which(executable)
