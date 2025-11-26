"""Configuration loading and management for Instagram monitor."""

import os
import platform
from dataclasses import dataclass, field
from typing import List, Optional


def _get_bool(key: str, default: bool) -> bool:
    """Get boolean from environment variable."""
    val = os.getenv(key, "").lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return default


def _get_int(key: str, default: int) -> int:
    """Get integer from environment variable."""
    val = os.getenv(key, "")
    if val:
        try:
            return int(val)
        except ValueError:
            pass
    return default


def _get_float(key: str, default: float) -> float:
    """Get float from environment variable."""
    val = os.getenv(key, "")
    if val:
        try:
            return float(val)
        except ValueError:
            pass
    return default


def _get_list(key: str, default: List[str]) -> List[str]:
    """Get list from comma-separated environment variable."""
    val = os.getenv(key, "")
    if val:
        return [item.strip() for item in val.split(",") if item.strip()]
    return default


@dataclass
class Config:
    """Configuration for Instagram monitor."""

    # Session login
    session_username: str = ""
    session_password: str = ""

    # SMTP settings
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_ssl: bool = True
    sender_email: str = ""
    receiver_email: str = ""

    # Notification settings
    status_notification: bool = False
    followers_notification: bool = False
    error_notification: bool = True
    x_notification: bool = False

    # X/Twitter credentials
    x_api_key: str = ""
    x_api_secret: str = ""
    x_access_token: str = ""
    x_access_token_secret: str = ""

    # Timing & intervals
    check_interval: int = 5400
    random_sleep_diff_low: int = 900
    random_sleep_diff_high: int = 180
    liveness_check_interval: int = 43200
    next_operation_delay: float = 0.7

    # Timezone
    local_timezone: str = "Auto"

    # Feature flags
    detect_changed_profile_pic: bool = True
    skip_session: bool = False
    skip_followers: bool = True  # Skip followers by default
    skip_followings: bool = False  # Fetch followings by default
    skip_getting_story_details: bool = False
    skip_getting_posts_details: bool = False
    get_more_post_details: bool = False

    # Anti-bot / human simulation
    be_human: bool = False
    daily_human_hits: int = 5
    my_hashtags: List[str] = field(default_factory=lambda: ["travel", "food", "nature"])
    be_human_verbose: bool = False
    enable_jitter: bool = False
    jitter_verbose: bool = False

    # User agents
    user_agent: str = ""
    user_agent_mobile: str = ""

    # Post checking hours
    check_posts_in_hours_range: bool = False
    min_h1: int = 0
    max_h1: int = 4
    min_h2: int = 11
    max_h2: int = 23

    # Logging & output
    disable_logging: bool = False
    csv_file: str = ""
    horizontal_line: int = 113
    clear_screen: bool = True

    # Signal handler settings
    check_signal_value: int = 300

    # Network settings
    check_internet_url: str = "https://www.instagram.com/"
    check_internet_timeout: int = 5

    # Paths
    imgcat_path: str = "imgcat"
    profile_pic_file_empty: str = ""

    # Firefox cookie paths
    firefox_macos_cookie: str = "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite"
    firefox_windows_cookie: str = "~/AppData/Roaming/Mozilla/Firefox/Profiles/*/cookies.sqlite"
    firefox_linux_cookie: str = "~/.mozilla/firefox/*/cookies.sqlite"

    # Internal state (not from config)
    target_usernames: List[str] = field(default_factory=list)

    def get_firefox_cookie_path(self) -> str:
        """Get Firefox cookie path for current OS."""
        system = platform.system()
        if system == "Darwin":
            return os.path.expanduser(self.firefox_macos_cookie)
        elif system == "Windows":
            return os.path.expanduser(self.firefox_windows_cookie)
        else:
            return os.path.expanduser(self.firefox_linux_cookie)

    def get_x_credentials(self) -> dict:
        """Get X/Twitter API credentials as dict."""
        return {
            "api_key": self.x_api_key,
            "api_secret": self.x_api_secret,
            "access_token": self.x_access_token,
            "access_token_secret": self.x_access_token_secret,
        }

    def has_x_credentials(self) -> bool:
        """Check if X/Twitter credentials are configured."""
        return bool(
            self.x_api_key
            and self.x_api_secret
            and self.x_access_token
            and self.x_access_token_secret
        )

    def has_smtp_credentials(self) -> bool:
        """Check if SMTP credentials are configured."""
        return bool(self.smtp_host and self.smtp_user and self.sender_email and self.receiver_email)


def load_config(env_file: Optional[str] = None) -> Config:
    """Load configuration from .env file and environment variables.

    Args:
        env_file: Optional path to .env file. Defaults to .env.local

    Returns:
        Config dataclass with all settings loaded
    """
    try:
        from dotenv import load_dotenv

        if env_file and os.path.exists(env_file):
            load_dotenv(env_file, override=True)
        elif os.path.exists(".env.local"):
            load_dotenv(".env.local", override=True)
        elif os.path.exists(".env"):
            load_dotenv(".env", override=True)
    except ImportError:
        pass

    return Config(
        # Session login
        session_username=os.getenv("SESSION_USERNAME", ""),
        session_password=os.getenv("SESSION_PASSWORD", ""),
        # SMTP settings
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=_get_int("SMTP_PORT", 587),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_ssl=_get_bool("SMTP_SSL", True),
        sender_email=os.getenv("SENDER_EMAIL", ""),
        receiver_email=os.getenv("RECEIVER_EMAIL", ""),
        # Notification settings
        status_notification=_get_bool("STATUS_NOTIFICATION", False),
        followers_notification=_get_bool("FOLLOWERS_NOTIFICATION", False),
        error_notification=_get_bool("ERROR_NOTIFICATION", True),
        x_notification=_get_bool("X_NOTIFICATION", False),
        # X/Twitter credentials
        x_api_key=os.getenv("X_API_KEY", ""),
        x_api_secret=os.getenv("X_API_SECRET", ""),
        x_access_token=os.getenv("X_ACCESS_TOKEN", ""),
        x_access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", ""),
        # Timing & intervals
        check_interval=_get_int("CHECK_INTERVAL", 5400),
        random_sleep_diff_low=_get_int("RANDOM_SLEEP_DIFF_LOW", 900),
        random_sleep_diff_high=_get_int("RANDOM_SLEEP_DIFF_HIGH", 180),
        liveness_check_interval=_get_int("LIVENESS_CHECK_INTERVAL", 43200),
        next_operation_delay=_get_float("NEXT_OPERATION_DELAY", 0.7),
        # Timezone
        local_timezone=os.getenv("LOCAL_TIMEZONE", "Auto"),
        # Feature flags
        detect_changed_profile_pic=_get_bool("DETECT_CHANGED_PROFILE_PIC", True),
        skip_session=_get_bool("SKIP_SESSION", False),
        skip_followers=_get_bool("SKIP_FOLLOWERS", True),  # Skip followers by default
        skip_followings=_get_bool("SKIP_FOLLOWINGS", False),  # Fetch followings by default
        skip_getting_story_details=_get_bool("SKIP_GETTING_STORY_DETAILS", False),
        skip_getting_posts_details=_get_bool("SKIP_GETTING_POSTS_DETAILS", False),
        get_more_post_details=_get_bool("GET_MORE_POST_DETAILS", False),
        # Anti-bot / human simulation
        be_human=_get_bool("BE_HUMAN", False),
        daily_human_hits=_get_int("DAILY_HUMAN_HITS", 5),
        my_hashtags=_get_list("MY_HASHTAGS", ["travel", "food", "nature"]),
        be_human_verbose=_get_bool("BE_HUMAN_VERBOSE", False),
        enable_jitter=_get_bool("ENABLE_JITTER", False),
        jitter_verbose=_get_bool("JITTER_VERBOSE", False),
        # User agents
        user_agent=os.getenv("USER_AGENT", ""),
        user_agent_mobile=os.getenv("USER_AGENT_MOBILE", ""),
        # Post checking hours
        check_posts_in_hours_range=_get_bool("CHECK_POSTS_IN_HOURS_RANGE", False),
        min_h1=_get_int("MIN_H1", 0),
        max_h1=_get_int("MAX_H1", 4),
        min_h2=_get_int("MIN_H2", 11),
        max_h2=_get_int("MAX_H2", 23),
        # Logging & output
        disable_logging=_get_bool("DISABLE_LOGGING", False),
        csv_file=os.getenv("CSV_FILE", ""),
        horizontal_line=_get_int("HORIZONTAL_LINE", 113),
        clear_screen=_get_bool("CLEAR_SCREEN", True),
        # Signal handler settings
        check_signal_value=_get_int("CHECK_SIGNAL_VALUE", 300),
        # Network settings
        check_internet_url=os.getenv("CHECK_INTERNET_URL", "https://www.instagram.com/"),
        check_internet_timeout=_get_int("CHECK_INTERNET_TIMEOUT", 5),
        # Paths
        imgcat_path=os.getenv("IMGCAT_PATH", "imgcat"),
        profile_pic_file_empty=os.getenv("PROFILE_PIC_FILE_EMPTY", ""),
        # Firefox cookie paths
        firefox_macos_cookie=os.getenv(
            "FIREFOX_MACOS_COOKIE",
            "~/Library/Application Support/Firefox/Profiles/*/cookies.sqlite",
        ),
        firefox_windows_cookie=os.getenv(
            "FIREFOX_WINDOWS_COOKIE",
            "~/AppData/Roaming/Mozilla/Firefox/Profiles/*/cookies.sqlite",
        ),
        firefox_linux_cookie=os.getenv(
            "FIREFOX_LINUX_COOKIE",
            "~/.mozilla/firefox/*/cookies.sqlite",
        ),
    )


def is_valid_timezone(timezone_str: str) -> bool:
    """Check if timezone string is valid.

    Args:
        timezone_str: Timezone name (e.g., 'Europe/Warsaw')

    Returns:
        True if valid timezone, False otherwise
    """
    try:
        import pytz

        return timezone_str in pytz.all_timezones
    except ImportError:
        return False


def get_local_timezone(config: Config) -> Optional[str]:
    """Get local timezone, auto-detecting if needed.

    Args:
        config: Config instance

    Returns:
        Timezone string or None if detection fails
    """
    if config.local_timezone and config.local_timezone.lower() != "auto":
        if is_valid_timezone(config.local_timezone):
            return config.local_timezone
        return None

    try:
        from tzlocal import get_localzone

        local_tz = get_localzone()
        return str(local_tz)
    except ImportError:
        return None
    except Exception:
        return None
