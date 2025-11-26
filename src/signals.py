"""Signal handlers for runtime control of Instagram monitor."""

import os
import signal
import sys
from typing import Any, Optional

from .config import Config
from .time_utils import display_time, get_cur_ts


class SignalState:
    """Mutable state container for signal handlers."""

    def __init__(self, config: Config):
        """Initialize signal state from config.

        Args:
            config: Config instance
        """
        self.status_notification = config.status_notification
        self.followers_notification = config.followers_notification
        self.check_interval = config.check_interval
        self.random_sleep_diff_low = config.random_sleep_diff_low
        self.random_sleep_diff_high = config.random_sleep_diff_high
        self.check_signal_value = config.check_signal_value
        self.horizontal_line = config.horizontal_line
        self.local_timezone = "UTC"  # Will be set after timezone detection
        self.stdout_backup: Optional[Any] = None


# Global signal state (needed because signal handlers can't take custom args)
_signal_state: Optional[SignalState] = None


def init_signal_state(config: Config, local_timezone: str = "UTC") -> SignalState:
    """Initialize global signal state.

    Args:
        config: Config instance
        local_timezone: Resolved timezone string

    Returns:
        SignalState instance
    """
    global _signal_state
    _signal_state = SignalState(config)
    _signal_state.local_timezone = local_timezone
    return _signal_state


def get_signal_state() -> Optional[SignalState]:
    """Get current signal state.

    Returns:
        SignalState instance or None
    """
    return _signal_state


def _print_timestamp() -> None:
    """Print current timestamp with separator."""
    if _signal_state:
        print(get_cur_ts(_signal_state.local_timezone, "Timestamp:\t\t"))
        print("─" * _signal_state.horizontal_line)


def signal_handler_exit(sig: int, frame: Any) -> None:
    """Handle SIGINT/SIGTERM for graceful exit.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    if _signal_state and _signal_state.stdout_backup:
        sys.stdout = _signal_state.stdout_backup
    print("\n* You pressed Ctrl+C, tool is terminated.")
    sys.exit(0)


def signal_handler_toggle_status(sig: int, frame: Any) -> None:
    """Handle SIGUSR1 to toggle status notifications.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    if not _signal_state:
        return

    _signal_state.status_notification = not _signal_state.status_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(
        f"* Email notifications: [new posts/reels/stories/followings/bio/profile picture = {_signal_state.status_notification}]"
    )
    _print_timestamp()


def signal_handler_toggle_followers(sig: int, frame: Any) -> None:
    """Handle SIGUSR2 to toggle followers notifications.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    if not _signal_state:
        return

    _signal_state.followers_notification = not _signal_state.followers_notification
    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(f"* Email notifications: [followers = {_signal_state.followers_notification}]")
    _print_timestamp()


def signal_handler_increase_interval(sig: int, frame: Any) -> None:
    """Handle SIGTRAP to increase check interval.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    if not _signal_state:
        return

    _signal_state.check_interval += _signal_state.check_signal_value

    if _signal_state.check_interval <= _signal_state.random_sleep_diff_low:
        check_interval_low = _signal_state.check_interval
    else:
        check_interval_low = _signal_state.check_interval - _signal_state.random_sleep_diff_low

    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(
        f"* Instagram timers: [check interval: {display_time(check_interval_low)} - "
        f"{display_time(_signal_state.check_interval + _signal_state.random_sleep_diff_high)}]"
    )
    _print_timestamp()


def signal_handler_decrease_interval(sig: int, frame: Any) -> None:
    """Handle SIGABRT to decrease check interval.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    if not _signal_state:
        return

    if (_signal_state.check_interval - _signal_state.random_sleep_diff_low - _signal_state.check_signal_value) > 0:
        _signal_state.check_interval -= _signal_state.check_signal_value

    if _signal_state.check_interval <= _signal_state.random_sleep_diff_low:
        check_interval_low = _signal_state.check_interval
    else:
        check_interval_low = _signal_state.check_interval - _signal_state.random_sleep_diff_low

    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")
    print(
        f"* Instagram timers: [check interval: {display_time(check_interval_low)} - "
        f"{display_time(_signal_state.check_interval + _signal_state.random_sleep_diff_high)}]"
    )
    _print_timestamp()


def signal_handler_reload_secrets(sig: int, frame: Any) -> None:
    """Handle SIGHUP to reload secrets from .env.

    Args:
        sig: Signal number
        frame: Current stack frame
    """
    if not _signal_state:
        return

    sig_name = signal.Signals(sig).name
    print(f"* Signal {sig_name} received")

    try:
        from dotenv import find_dotenv, load_dotenv

        env_path = find_dotenv()
        if os.path.exists(".env.local"):
            env_path = ".env.local"

        if env_path:
            load_dotenv(env_path, override=True)
            print(f"* Reloaded environment from {env_path}")
        else:
            print("* No .env file found, skipping env-var reload")
    except ImportError:
        print("* python-dotenv not installed, skipping env-var reload")

    _print_timestamp()


def register_signal_handlers(config: Config, local_timezone: str = "UTC") -> SignalState:
    """Register all signal handlers.

    Args:
        config: Config instance
        local_timezone: Resolved timezone string

    Returns:
        SignalState instance
    """
    state = init_signal_state(config, local_timezone)

    # Exit handler
    signal.signal(signal.SIGINT, signal_handler_exit)
    signal.signal(signal.SIGTERM, signal_handler_exit)

    # Unix-only signals
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, signal_handler_toggle_status)
    if hasattr(signal, "SIGUSR2"):
        signal.signal(signal.SIGUSR2, signal_handler_toggle_followers)
    if hasattr(signal, "SIGTRAP"):
        signal.signal(signal.SIGTRAP, signal_handler_increase_interval)
    if hasattr(signal, "SIGABRT"):
        signal.signal(signal.SIGABRT, signal_handler_decrease_interval)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, signal_handler_reload_secrets)

    return state
