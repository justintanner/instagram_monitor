"""Configuration loading for instagram_monitor shared modules."""

import os

SECRET_KEYS = (
    "X_API_KEY",
    "X_API_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
)


def load_env_config(env_file=None):
    """Load configuration from .env file and environment variables.

    Args:
        env_file: Optional path to .env file. If None, auto-searches.

    Returns:
        Dict with configuration values from environment.
    """
    try:
        from dotenv import load_dotenv, find_dotenv

        if env_file:
            if os.path.exists(env_file):
                load_dotenv(env_file, override=True)
        else:
            env_path = find_dotenv()
            if env_path:
                load_dotenv(env_path, override=True)
    except ImportError:
        pass

    config = {}
    for key in SECRET_KEYS:
        config[key] = os.getenv(key, "")
    return config


def get_x_credentials(config=None):
    """Get X API credentials from config dict or environment.

    Args:
        config: Optional dict with credential keys. If None, loads from env.

    Returns:
        Dict with api_key, api_secret, access_token, access_token_secret.
    """
    if config is None:
        config = load_env_config()
    return {
        "api_key": config.get("X_API_KEY", ""),
        "api_secret": config.get("X_API_SECRET", ""),
        "access_token": config.get("X_ACCESS_TOKEN", ""),
        "access_token_secret": config.get("X_ACCESS_TOKEN_SECRET", ""),
    }
