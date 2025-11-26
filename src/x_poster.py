"""X/Twitter posting functionality for instagram_monitor."""

import os

try:
    import tweepy

    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False


def post_to_x(text, image_path="", credentials=None):
    """Post a tweet to X/Twitter with optional image.

    Args:
        text: Tweet text (max 280 chars)
        image_path: Optional path to image file to attach
        credentials: Dict with api_key, api_secret, access_token, access_token_secret.
                    If None, reads from environment variables via config module.

    Returns:
        0 on success, 1 on failure.
    """
    if not TWEEPY_AVAILABLE:
        print("* Error: tweepy not available, cannot post to X")
        return 1

    if credentials is None:
        from src.config import get_x_credentials

        credentials = get_x_credentials()

    api_key = credentials.get("api_key", "")
    api_secret = credentials.get("api_secret", "")
    access_token = credentials.get("access_token", "")
    access_token_secret = credentials.get("access_token_secret", "")

    if not api_key or api_key == "your_api_key":
        print("* Error: X API credentials not configured")
        return 1

    if not api_secret or not access_token or not access_token_secret:
        print("* Error: X API credentials incomplete")
        return 1

    try:
        # For media upload, we need v1.1 API
        auth = tweepy.OAuth1UserHandler(
            api_key, api_secret, access_token, access_token_secret
        )
        api = tweepy.API(auth)

        # v2 client for posting tweets
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )

        media_ids = None
        if image_path and os.path.exists(image_path):
            media = api.media_upload(image_path)
            media_ids = [media.media_id]

        response = client.create_tweet(text=text, media_ids=media_ids)

        if response and response.data:
            tweet_id = response.data["id"]
            print(f"* Posted to X: https://x.com/i/status/{tweet_id}")
            return 0
        else:
            print("* Error: Failed to post to X (no response data)")
            return 1

    except Exception as e:
        print(f"* Error posting to X: {e}")
        return 1


def format_follow_tweet(user, display_name, added_list, removed_list):
    """Format a tweet for follow/unfollow events.

    Args:
        user: Instagram username
        display_name: User's display name (full name)
        added_list: List of usernames the user started following
        removed_list: List of usernames the user unfollowed

    Returns:
        Formatted tweet text (max 280 chars).
    """
    lines = []
    display_part = f" ({display_name})" if display_name else ""

    if added_list:
        count = len(added_list)
        person_word = "person" if count == 1 else "people"
        lines.append(
            f"🔥 {user}{display_part} started following {count} {person_word}:\n"
        )
        for username in added_list[:5]:  # Limit to 5 to stay under 280 chars
            lines.append(f"✅ {username}")
            lines.append(f"🔗 https://instagram.com/{username}")
        if len(added_list) > 5:
            lines.append(f"... and {len(added_list) - 5} more")

    if removed_list:
        if added_list:
            lines.append("")  # Separator
        count = len(removed_list)
        person_word = "person" if count == 1 else "people"
        lines.append(
            f"💔 {user}{display_part} unfollowed {count} {person_word}:\n"
        )
        for username in removed_list[:5]:
            lines.append(f"❌ {username}")
            lines.append(f"🔗 https://instagram.com/{username}")
        if len(removed_list) > 5:
            lines.append(f"... and {len(removed_list) - 5} more")

    tweet = "\n".join(lines)

    # Truncate if too long (280 char limit)
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."

    return tweet
