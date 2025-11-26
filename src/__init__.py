"""Instagram Monitor - Modular OSINT tool for tracking Instagram users."""

from .config import Config, load_config
from .client import init_bot, get_profile
from .logger import Logger, check_internet, clear_screen
from .monitor import monitor_users, UserState
from .notifications import send_email, post_to_x, format_follow_tweet
from .persistence import (
    ensure_data_dirs,
    get_data_path,
    get_log_path,
    get_image_path,
    get_followers_path,
    get_followings_path,
)
from .profile_card import generate_profile_card
from .signals import register_signal_handlers
from .time_utils import display_time, calculate_timespan, get_cur_ts

__all__ = [
    # Config
    "Config",
    "load_config",
    # Client
    "init_bot",
    "get_profile",
    # Logger
    "Logger",
    "check_internet",
    "clear_screen",
    # Monitor
    "monitor_users",
    "UserState",
    # Notifications
    "send_email",
    "post_to_x",
    "format_follow_tweet",
    # Persistence
    "ensure_data_dirs",
    "get_data_path",
    "get_log_path",
    "get_image_path",
    "get_followers_path",
    "get_followings_path",
    # Profile card
    "generate_profile_card",
    # Signals
    "register_signal_handlers",
    # Time utils
    "display_time",
    "calculate_timespan",
    "get_cur_ts",
]
