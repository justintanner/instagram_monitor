#!/usr/bin/env python3
"""
Instagram Monitor - Entry Point

OSINT tool for real-time monitoring of Instagram users' activities and profile changes.
"""

import argparse
import sys

VERSION = "2.0"


def main():
    """Main entry point for Instagram monitor."""
    from src.client import get_firefox_cookiefile, import_firefox_session
    from src.config import load_config
    from src.logger import check_internet, clear_screen
    from src.monitor import monitor_users
    from src.notifications import send_test_email, send_test_x

    # Handle --version early
    if "--version" in sys.argv:
        print(f"instagram-monitor v{VERSION}")
        sys.exit(0)

    parser = argparse.ArgumentParser(
        prog="instagram-monitor",
        description="Monitor Instagram users' activities and send customizable alerts",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Positional
    parser.add_argument(
        "usernames",
        nargs="*",
        metavar="TARGET_USERNAME",
        help="Instagram username(s) to monitor (supports multiple)",
        type=str,
    )

    # Version
    parser.add_argument("--version", action="version", version=f"%(prog)s v{VERSION}")

    # Configuration
    conf = parser.add_argument_group("Configuration")
    conf.add_argument(
        "--env-file",
        dest="env_file",
        metavar="PATH",
        help="Path to .env file (default: .env.local)",
    )

    # Session login credentials
    creds = parser.add_argument_group("Session login credentials")
    creds.add_argument(
        "-u",
        "--session-username",
        dest="session_username",
        metavar="USERNAME",
        type=str,
        help="Instagram username for session login",
    )
    creds.add_argument(
        "-p",
        "--session-password",
        dest="session_password",
        metavar="PASSWORD",
        type=str,
        help="Instagram password for session login",
    )

    # Notifications
    notify = parser.add_argument_group("Notifications")
    notify.add_argument(
        "-s",
        "--notify-status",
        dest="status_notification",
        action="store_true",
        default=None,
        help="Email on profile changes (posts, bio, follows, etc.)",
    )
    notify.add_argument(
        "-m",
        "--notify-followers",
        dest="followers_notification",
        action="store_true",
        default=None,
        help="Email on new followers",
    )
    notify.add_argument(
        "-e",
        "--no-error-notify",
        dest="error_notification",
        action="store_false",
        default=None,
        help="Disable email on errors",
    )
    notify.add_argument(
        "--send-test-email",
        dest="send_test_email",
        action="store_true",
        help="Send test email and exit",
    )
    notify.add_argument(
        "-x",
        "--x-notification",
        dest="x_notification",
        action="store_true",
        default=None,
        help="Post to X/Twitter on follow/unfollow events",
    )
    notify.add_argument(
        "--send-test-x",
        dest="send_test_x",
        action="store_true",
        help="Send test post to X and exit",
    )

    # Intervals
    times = parser.add_argument_group("Intervals & timers")
    times.add_argument(
        "-c",
        "--check-interval",
        dest="check_interval",
        metavar="SECONDS",
        type=int,
        help="Time between checks (default: 5400)",
    )
    times.add_argument(
        "-i",
        "--random-diff-low",
        dest="random_sleep_diff_low",
        metavar="SECONDS",
        type=int,
        help="Subtract up to this value from check-interval",
    )
    times.add_argument(
        "-j",
        "--random-diff-high",
        dest="random_sleep_diff_high",
        metavar="SECONDS",
        type=int,
        help="Add up to this value to check-interval",
    )

    # Session options
    session_opts = parser.add_argument_group("Session options")
    session_opts.add_argument(
        "-l",
        "--skip-session",
        dest="skip_session",
        action="store_true",
        default=None,
        help="Skip session login (anonymous mode)",
    )
    session_opts.add_argument(
        "-f",
        "--skip-followers",
        dest="skip_followers",
        action="store_true",
        default=None,
        help="Do not fetch followers list",
    )
    session_opts.add_argument(
        "-g",
        "--skip-followings",
        dest="skip_followings",
        action="store_true",
        default=None,
        help="Do not fetch followings list",
    )
    session_opts.add_argument(
        "-r",
        "--skip-story-details",
        dest="skip_getting_story_details",
        action="store_true",
        default=None,
        help="Do not fetch detailed story info",
    )
    session_opts.add_argument(
        "-w",
        "--skip-post-details",
        dest="skip_getting_posts_details",
        action="store_true",
        default=None,
        help="Do not fetch detailed post info",
    )
    session_opts.add_argument(
        "-t",
        "--more-post-details",
        dest="get_more_post_details",
        action="store_true",
        default=None,
        help="Fetch extra post details (comments and likes)",
    )
    session_opts.add_argument(
        "--user-agent",
        dest="user_agent",
        metavar="UA",
        type=str,
        help="Custom web browser user agent",
    )
    session_opts.add_argument(
        "--user-agent-mobile",
        dest="user_agent_mobile",
        metavar="UA",
        type=str,
        help="Custom mobile user agent",
    )
    session_opts.add_argument(
        "--be-human",
        dest="be_human",
        action="store_true",
        default=None,
        help="Simulate human behavior with random actions",
    )
    session_opts.add_argument(
        "--enable-jitter",
        dest="enable_jitter",
        action="store_true",
        default=None,
        help="Enable HTTP request jitter and back-off",
    )

    # Features
    opts = parser.add_argument_group("Features & output")
    opts.add_argument(
        "-k",
        "--no-profile-pic-detect",
        dest="detect_changed_profile_pic",
        action="store_false",
        default=None,
        help="Disable profile picture change detection",
    )
    opts.add_argument(
        "-b",
        "--csv-file",
        dest="csv_file",
        metavar="FILE",
        type=str,
        help="Write activities to CSV file",
    )
    opts.add_argument(
        "-d",
        "--disable-logging",
        dest="disable_logging",
        action="store_true",
        default=None,
        help="Disable logging to file",
    )

    # Firefox session import
    import_grp = parser.add_argument_group("Firefox session import")
    import_grp.add_argument(
        "--import-firefox-session",
        action="store_true",
        help="Import Firefox session cookies and exit",
    )
    import_grp.add_argument(
        "--cookie-file",
        dest="cookie_file",
        metavar="PATH",
        help="Path to Firefox cookies.sqlite",
    )
    import_grp.add_argument(
        "--session-file",
        dest="session_file",
        metavar="PATH",
        help="Path to save Instaloader session",
    )

    args = parser.parse_args()

    # Load config from .env
    config = load_config(args.env_file)

    # Apply CLI overrides
    if args.session_username:
        config.session_username = args.session_username
    if args.session_password:
        config.session_password = args.session_password
    if args.status_notification is not None:
        config.status_notification = args.status_notification
    if args.followers_notification is not None:
        config.followers_notification = args.followers_notification
    if args.error_notification is not None:
        config.error_notification = args.error_notification
    if args.x_notification is not None:
        config.x_notification = args.x_notification
    if args.check_interval:
        config.check_interval = args.check_interval
    if args.random_sleep_diff_low:
        config.random_sleep_diff_low = args.random_sleep_diff_low
    if args.random_sleep_diff_high:
        config.random_sleep_diff_high = args.random_sleep_diff_high
    if args.skip_session is not None:
        config.skip_session = args.skip_session
    if args.skip_followers is not None:
        config.skip_followers = args.skip_followers
    if args.skip_followings is not None:
        config.skip_followings = args.skip_followings
    if args.skip_getting_story_details is not None:
        config.skip_getting_story_details = args.skip_getting_story_details
    if args.skip_getting_posts_details is not None:
        config.skip_getting_posts_details = args.skip_getting_posts_details
    if args.get_more_post_details is not None:
        config.get_more_post_details = args.get_more_post_details
    if args.user_agent:
        config.user_agent = args.user_agent
    if args.user_agent_mobile:
        config.user_agent_mobile = args.user_agent_mobile
    if args.be_human is not None:
        config.be_human = args.be_human
    if args.enable_jitter is not None:
        config.enable_jitter = args.enable_jitter
    if args.detect_changed_profile_pic is not None:
        config.detect_changed_profile_pic = args.detect_changed_profile_pic
    if args.csv_file:
        config.csv_file = args.csv_file
    if args.disable_logging is not None:
        config.disable_logging = args.disable_logging

    # Set target usernames
    config.target_usernames = args.usernames

    # Handle special commands
    if args.import_firefox_session:
        cookie_file = args.cookie_file or get_firefox_cookiefile(config)
        import_firefox_session(cookie_file, args.session_file)
        sys.exit(0)

    if args.send_test_email:
        send_test_email(config)
        sys.exit(0)

    if args.send_test_x:
        send_test_x(config)
        sys.exit(0)

    # Validate required arguments
    if not args.usernames:
        parser.print_help(sys.stderr)
        print("\nError: At least one TARGET_USERNAME is required")
        sys.exit(1)

    # Clear screen and print header
    clear_screen(config.clear_screen)
    print(f"Instagram Monitor v{VERSION}\n")

    # Check internet connectivity
    if not check_internet(config.check_internet_url, config.check_internet_timeout, config.user_agent):
        sys.exit(1)

    # Start monitoring
    monitor_users(config)


if __name__ == "__main__":
    main()
