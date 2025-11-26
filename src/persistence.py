"""File I/O and persistence utilities for Instagram monitor."""

import csv
import json
import os
import shutil
from itertools import zip_longest
from pathlib import Path
from typing import Any, List, Optional, Tuple

import requests

# Data directory structure
DATA_DIR = Path("data")
LOGS_DIR = DATA_DIR / "logs"
IMAGES_DIR = DATA_DIR / "images"

# CSV field names
CSV_FIELDNAMES = ["Date", "Type", "Old", "New"]

# Default network timeout
FUNCTION_TIMEOUT = 15


def ensure_data_dirs() -> None:
    """Create data directory structure if it doesn't exist."""
    DATA_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)


def get_data_path(filename: str) -> Path:
    """Get path for a file in the data directory.

    Args:
        filename: Filename (without path)

    Returns:
        Full path in data directory
    """
    return DATA_DIR / filename


def get_log_path(username: str) -> Path:
    """Get log file path for a user.

    Args:
        username: Instagram username

    Returns:
        Path to log file
    """
    return LOGS_DIR / f"monitor_{username}.log"


def get_image_path(username: str, suffix: str = "") -> Path:
    """Get image file path for a user.

    Args:
        username: Instagram username
        suffix: Optional suffix (e.g., "_old", "_tmp", "_20240101_1200")

    Returns:
        Path to image file
    """
    return IMAGES_DIR / f"{username}_profile_pic{suffix}.jpeg"


def get_followers_path(username: str) -> Path:
    """Get followers JSON file path for a user.

    Args:
        username: Instagram username

    Returns:
        Path to followers JSON file
    """
    return DATA_DIR / f"{username}_followers.json"


def get_followings_path(username: str) -> Path:
    """Get followings JSON file path for a user.

    Args:
        username: Instagram username

    Returns:
        Path to followings JSON file
    """
    return DATA_DIR / f"{username}_followings.json"


def get_media_path(username: str, media_type: str, timestamp: str, extension: str) -> Path:
    """Get media file path (post/reel/story).

    Args:
        username: Instagram username
        media_type: Type of media (post, reel, story)
        timestamp: Timestamp string for filename
        extension: File extension (jpeg, mp4)

    Returns:
        Path to media file
    """
    return IMAGES_DIR / f"{username}_{media_type}_{timestamp}.{extension}"


def get_profile_card_path(username: str) -> Path:
    """Get profile card image path.

    Args:
        username: Instagram username

    Returns:
        Path to profile card image (in /tmp)
    """
    return Path("/tmp") / f"{username}_card.jpeg"


def init_csv_file(csv_file_path: str) -> None:
    """Initialize CSV file with headers if needed.

    Args:
        csv_file_path: Path to CSV file

    Raises:
        RuntimeError: If file cannot be initialized
    """
    try:
        if not os.path.isfile(csv_file_path) or os.path.getsize(csv_file_path) == 0:
            with open(csv_file_path, "a", newline="", buffering=1, encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_NONNUMERIC)
                writer.writeheader()
    except Exception as e:
        raise RuntimeError(f"Could not initialize CSV file '{csv_file_path}': {e}")


def write_csv_entry(
    csv_file_path: str, timestamp: str, object_type: str, old: str, new: str
) -> None:
    """Write entry to CSV file.

    Args:
        csv_file_path: Path to CSV file
        timestamp: Timestamp string
        object_type: Type of change
        old: Old value
        new: New value

    Raises:
        RuntimeError: If write fails
    """
    try:
        with open(csv_file_path, "a", newline="", buffering=1, encoding="utf-8") as csv_file:
            csvwriter = csv.DictWriter(
                csv_file, fieldnames=CSV_FIELDNAMES, quoting=csv.QUOTE_NONNUMERIC
            )
            csvwriter.writerow({"Date": timestamp, "Type": object_type, "Old": old, "New": new})
    except Exception as e:
        raise RuntimeError(f"Failed to write to CSV file '{csv_file_path}': {e}")


def save_pic_video(
    url: str,
    file_path: str,
    user_agent: str = "",
    custom_mdate_ts: int = 0,
    timeout: int = FUNCTION_TIMEOUT,
    convert_utc_str_func: Optional[Any] = None,
) -> bool:
    """Download and save image or video from URL.

    Args:
        url: URL to download from
        file_path: Path to save file
        user_agent: User agent for request
        custom_mdate_ts: Custom modification timestamp
        timeout: Request timeout
        convert_utc_str_func: Function to convert UTC string to datetime

    Returns:
        True if successful, False otherwise
    """
    try:
        headers = {"User-Agent": user_agent} if user_agent else {}
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()

        url_time = response.headers.get("last-modified")
        url_time_in_tz_ts = 0

        if url_time and not custom_mdate_ts and convert_utc_str_func:
            url_time_in_tz = convert_utc_str_func(url_time)
            if url_time_in_tz:
                url_time_in_tz_ts = int(url_time_in_tz.timestamp())

        if response.status_code == 200:
            # Ensure parent directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "wb") as f:
                response.raw.decode_content = True
                shutil.copyfileobj(response.raw, f)

            if url_time_in_tz_ts and not custom_mdate_ts:
                os.utime(file_path, (url_time_in_tz_ts, url_time_in_tz_ts))
            elif custom_mdate_ts:
                os.utime(file_path, (custom_mdate_ts, custom_mdate_ts))

        return True
    except Exception:
        return False


def compare_images(file1: str, file2: str) -> bool:
    """Compare two image files byte by byte.

    Args:
        file1: Path to first file
        file2: Path to second file

    Returns:
        True if files are identical, False otherwise
    """
    if not os.path.isfile(file1) or not os.path.isfile(file2):
        return False
    try:
        with open(file1, "rb") as f1, open(file2, "rb") as f2:
            for line1, line2 in zip_longest(f1, f2, fillvalue=None):
                if line1 != line2:
                    return False
            return True
    except Exception as e:
        print(f"* Error while comparing files: {e}")
        return False


def load_json_file(file_path: str) -> Optional[Any]:
    """Load JSON data from file.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON data, or None if file doesn't exist or is invalid
    """
    if not os.path.isfile(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json_file(file_path: str, data: Any) -> bool:
    """Save data to JSON file.

    Args:
        file_path: Path to JSON file
        data: Data to save

    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure parent directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def load_followers(username: str) -> Tuple[int, List[str]]:
    """Load followers list from file.

    Args:
        username: Instagram username

    Returns:
        Tuple of (count, list of follower usernames)
    """
    data = load_json_file(str(get_followers_path(username)))
    if data and isinstance(data, list) and len(data) >= 2:
        return data[0], data[1]
    return 0, []


def save_followers(username: str, count: int, followers: List[str]) -> bool:
    """Save followers list to file.

    Args:
        username: Instagram username
        count: Follower count
        followers: List of follower usernames

    Returns:
        True if successful, False otherwise
    """
    return save_json_file(str(get_followers_path(username)), [count, followers])


def load_followings(username: str) -> Tuple[int, List[str]]:
    """Load followings list from file.

    Args:
        username: Instagram username

    Returns:
        Tuple of (count, list of following usernames)
    """
    data = load_json_file(str(get_followings_path(username)))
    if data and isinstance(data, list) and len(data) >= 2:
        return data[0], data[1]
    return 0, []


def save_followings(username: str, count: int, followings: List[str]) -> bool:
    """Save followings list to file.

    Args:
        username: Instagram username
        count: Following count
        followings: List of following usernames

    Returns:
        True if successful, False otherwise
    """
    return save_json_file(str(get_followings_path(username)), [count, followings])
