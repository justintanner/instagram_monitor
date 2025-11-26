"""Notification functionality (email, X/Twitter) for Instagram monitor."""

import ipaddress
import os
import re
import smtplib
import ssl
from email.header import Header
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from .config import Config

try:
    import tweepy

    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False


def send_email(
    config: Config,
    subject: str,
    body: str,
    body_html: str = "",
    image_file: str = "",
    image_name: str = "image1",
    smtp_timeout: int = 15,
) -> int:
    """Send email notification via SMTP.

    Args:
        config: Config instance with SMTP settings
        subject: Email subject
        body: Plain text body
        body_html: HTML body (optional)
        image_file: Path to image attachment (optional)
        image_name: CID name for inline image
        smtp_timeout: SMTP connection timeout

    Returns:
        0 on success, 1 on failure
    """
    fqdn_re = re.compile(
        r"(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}\.?$)"
    )
    email_re = re.compile(r"[^@]+@[^@]+\.[^@]+")

    # Validate SMTP host
    try:
        ipaddress.ip_address(str(config.smtp_host))
    except ValueError:
        if not fqdn_re.search(str(config.smtp_host)):
            print("Error sending email - SMTP settings are incorrect (invalid IP address/FQDN in SMTP_HOST)")
            return 1

    # Validate port
    try:
        port = int(config.smtp_port)
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("Error sending email - SMTP settings are incorrect (invalid port number in SMTP_PORT)")
        return 1

    # Validate email addresses
    if not email_re.search(str(config.sender_email)) or not email_re.search(str(config.receiver_email)):
        print("Error sending email - SMTP settings are incorrect (invalid email in SENDER_EMAIL or RECEIVER_EMAIL)")
        return 1

    # Validate credentials
    if (
        not config.smtp_user
        or not isinstance(config.smtp_user, str)
        or config.smtp_user == "your_smtp_user"
        or not config.smtp_password
        or not isinstance(config.smtp_password, str)
        or config.smtp_password == "your_smtp_password"
    ):
        print("Error sending email - SMTP settings are incorrect (check SMTP_USER & SMTP_PASSWORD variables)")
        return 1

    # Validate subject
    if not subject or not isinstance(subject, str):
        print("Error sending email - SMTP settings are incorrect (subject is not a string or is empty)")
        return 1

    # Validate body
    if not body and not body_html:
        print("Error sending email - SMTP settings are incorrect (body and body_html cannot be empty at the same time)")
        return 1

    try:
        if config.smtp_ssl:
            ssl_context = ssl.create_default_context()
            smtp_obj = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=smtp_timeout)
            smtp_obj.starttls(context=ssl_context)
        else:
            smtp_obj = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=smtp_timeout)

        smtp_obj.login(config.smtp_user, config.smtp_password)

        email_msg = MIMEMultipart("alternative")
        email_msg["From"] = config.sender_email
        email_msg["To"] = config.receiver_email
        email_msg["Subject"] = str(Header(subject, "utf-8"))

        if body:
            part1 = MIMEText(body.encode("utf-8"), "plain", _charset="utf-8")
            email_msg.attach(part1)

        if body_html:
            part2 = MIMEText(body_html.encode("utf-8"), "html", _charset="utf-8")
            email_msg.attach(part2)

        if image_file and os.path.exists(image_file):
            with open(image_file, "rb") as fp:
                img_part = MIMEImage(fp.read())
            img_part.add_header("Content-ID", f"<{image_name}>")
            email_msg.attach(img_part)

        smtp_obj.sendmail(config.sender_email, config.receiver_email, email_msg.as_string())
        smtp_obj.quit()

    except Exception as e:
        print(f"Error sending email: {e}")
        return 1

    return 0


def post_to_x(
    text: str,
    image_path: str = "",
    credentials: Optional[dict] = None,
    config: Optional[Config] = None,
) -> int:
    """Post a tweet to X/Twitter with optional image.

    Args:
        text: Tweet text (max 280 chars)
        image_path: Optional path to image file to attach
        credentials: Dict with api_key, api_secret, access_token, access_token_secret
        config: Config instance (used if credentials not provided)

    Returns:
        0 on success, 1 on failure
    """
    if not TWEEPY_AVAILABLE:
        print("* Error: tweepy not available, cannot post to X")
        return 1

    if credentials is None:
        if config is None:
            print("* Error: No credentials or config provided for X posting")
            return 1
        credentials = config.get_x_credentials()

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
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
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


def format_follow_tweet(
    username: str,
    display_name: str,
    added_list: List[str],
    removed_list: List[str],
) -> str:
    """Format a tweet for follow/unfollow events.

    Args:
        username: Instagram username
        display_name: User's display name (full name)
        added_list: List of usernames the user started following
        removed_list: List of usernames the user unfollowed

    Returns:
        Formatted tweet text (max 280 chars)
    """
    lines = []
    display_part = f" ({display_name})" if display_name else ""

    if added_list:
        count = len(added_list)
        person_word = "person" if count == 1 else "people"
        lines.append(f"🔥 {username}{display_part} started following {count} {person_word}:\n")
        for name in added_list[:5]:
            lines.append(f"✅ {name}")
            lines.append(f"🔗 https://instagram.com/{name}")
        if len(added_list) > 5:
            lines.append(f"... and {len(added_list) - 5} more")

    if removed_list:
        if added_list:
            lines.append("")
        count = len(removed_list)
        person_word = "person" if count == 1 else "people"
        lines.append(f"💔 {username}{display_part} unfollowed {count} {person_word}:\n")
        for name in removed_list[:5]:
            lines.append(f"❌ {name}")
            lines.append(f"🔗 https://instagram.com/{name}")
        if len(removed_list) > 5:
            lines.append(f"... and {len(removed_list) - 5} more")

    tweet = "\n".join(lines)

    # Truncate if too long (280 char limit)
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."

    return tweet


def send_test_email(config: Config) -> int:
    """Send a test email to verify SMTP configuration.

    Args:
        config: Config instance

    Returns:
        0 on success, 1 on failure
    """
    subject = "Instagram Monitor - Test Email"
    body = "This is a test email from Instagram Monitor.\n\nIf you received this, your SMTP configuration is working correctly."

    print(f"Sending test email to {config.receiver_email}...")
    result = send_email(config, subject, body)

    if result == 0:
        print("Test email sent successfully!")
    else:
        print("Failed to send test email. Check your SMTP configuration.")

    return result


def send_test_x(config: Config) -> int:
    """Send a test post to X/Twitter.

    Args:
        config: Config instance

    Returns:
        0 on success, 1 on failure
    """
    text = "🧪 Test post from Instagram Monitor"

    print("Sending test post to X...")
    result = post_to_x(text, config=config)

    if result == 0:
        print("Test post sent successfully!")
    else:
        print("Failed to send test post. Check your X API credentials.")

    return result
