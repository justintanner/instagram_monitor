"""Core monitoring loop and user state management for Instagram monitor."""

import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import instaloader

from .client import (
    get_profile,
    get_total_reels_count,
    init_bot,
    simulate_human_actions,
)
from .config import Config, get_local_timezone
from .notifications import format_follow_tweet, post_to_x, send_email
from .persistence import (
    compare_images,
    ensure_data_dirs,
    get_followers_path,
    get_followings_path,
    get_image_path,
    get_log_path,
    init_csv_file,
    load_followers,
    load_followings,
    save_followings,
    save_pic_video,
)
from .profile_card import generate_profile_card
from .signals import get_signal_state, register_signal_handlers
from .time_utils import (
    display_time,
    get_cur_ts,
    get_range_of_dates_from_tss,
    now_local,
    print_cur_ts,
    randomize_number,
)


@dataclass
class UserState:
    """State container for a monitored user."""

    username: str
    bot: Any
    config: Config
    local_timezone: str

    # Profile data
    insta_username: str = ""
    insta_userid: int = 0
    full_name: str = ""
    followers_count: int = 0
    followings_count: int = 0
    bio: str = ""
    is_private: bool = False
    followed_by_viewer: bool = False
    can_view: bool = False
    posts_count: int = 0
    reels_count: int = 0
    has_story: bool = False
    profile_image_url: str = ""

    # Previous values for comparison
    followers_count_old: int = 0
    followings_count_old: int = 0
    bio_old: str = ""
    is_private_old: bool = False
    followed_by_viewer_old: bool = False
    posts_count_old: int = 0
    reels_count_old: int = 0
    stories_count: int = 0
    stories_count_old: int = 0

    # Lists
    followers: List[str] = field(default_factory=list)
    followings: List[str] = field(default_factory=list)
    followers_old: List[str] = field(default_factory=list)
    followings_old: List[str] = field(default_factory=list)
    processed_stories: List[Dict] = field(default_factory=list)

    # Timestamps
    highest_post_ts: int = 0
    highest_post_dt: Optional[datetime] = None

    # Flags
    initialized: bool = False
    error: Optional[str] = None
    story_flag: bool = False
    email_sent: bool = False
    alive_counter: int = 0


def init_user_state(
    username: str,
    bot: instaloader.Instaloader,
    config: Config,
    local_timezone: str,
) -> UserState:
    """Initialize state for a single user.

    Args:
        username: Instagram username to monitor
        bot: Instaloader instance
        config: Config instance
        local_timezone: Resolved timezone string

    Returns:
        UserState instance
    """
    state = UserState(
        username=username,
        bot=bot,
        config=config,
        local_timezone=local_timezone,
    )

    try:
        if config.csv_file:
            csv_path = str(get_log_path(username).with_suffix(".csv"))
            init_csv_file(csv_path)
    except Exception as e:
        print(f"* Error initializing CSV for {username}: {e}")

    try:
        print(f"\nSneaking into Instagram for user {username} ... (be patient, secrets take time)")

        profile = get_profile(bot, username)
        time.sleep(config.next_operation_delay)

        state.insta_username = profile.username
        state.insta_userid = profile.userid
        state.full_name = profile.full_name
        state.followers_count = profile.followers
        state.followings_count = profile.followees
        state.bio = profile.biography
        state.is_private = profile.is_private
        state.followed_by_viewer = profile.followed_by_viewer
        state.can_view = (not profile.is_private) or profile.followed_by_viewer
        state.posts_count = profile.mediacount

        if not config.skip_session and state.can_view:
            state.reels_count = get_total_reels_count(username, bot, config.skip_session)
        else:
            state.reels_count = 0

        if not state.is_private:
            if bot.context.is_logged_in:
                state.has_story = profile.has_public_story
            else:
                state.has_story = False
        elif bot.context.is_logged_in and state.followed_by_viewer:
            story = next(bot.get_stories(userids=[state.insta_userid]), None)
            state.has_story = bool(story and story.itemcount)
        else:
            state.has_story = False

        state.profile_image_url = profile.profile_pic_url_no_iphone

        # Initialize old values
        state.followers_count_old = state.followers_count
        state.followings_count_old = state.followings_count
        state.bio_old = state.bio
        state.posts_count_old = state.posts_count
        state.reels_count_old = state.reels_count
        state.is_private_old = state.is_private
        state.followed_by_viewer_old = state.followed_by_viewer

        # Load existing followers from file
        followers_path = get_followers_path(username)
        if followers_path.exists():
            try:
                count, followers = load_followers(username)
                if count > 0:
                    state.followers_count_old = count
                    state.followers_old = followers
                    if state.followers_count == count:
                        state.followers = followers
                    print(f"* Followers ({count}) loaded from '{followers_path}'")
            except Exception as e:
                print(f"* Cannot load followers list: {e}")

        # Load existing followings from file
        followings_path = get_followings_path(username)
        if followings_path.exists():
            try:
                count, followings = load_followings(username)
                if count > 0:
                    state.followings_count_old = count
                    state.followings_old = followings
                    if state.followings_count == count:
                        state.followings = followings
                    print(f"* Followings ({count}) loaded from '{followings_path}'")
            except Exception as e:
                print(f"* Cannot load followings list: {e}")

        # Fetch initial followings if no file exists
        if (
            not followings_path.exists()
            and not config.skip_session
            and not config.skip_followings
            and state.can_view
            and state.followings_count > 0
        ):
            try:
                print(f"* Fetching initial followings list for {username}...")
                followings = [followee.username for followee in profile.get_followees()]
                if followings:
                    state.followings = followings
                    state.followings_old = followings
                    save_followings(username, state.followings_count, followings)
                    print(f"* Followings ({len(followings)}) saved")
            except Exception as e:
                print(f"* Error fetching initial followings: {type(e).__name__}: {e}")

        # Initialize post tracking
        state.highest_post_ts = int(time.time())
        state.highest_post_dt = now_local(local_timezone)

        # Print user info
        if bot.context.is_logged_in:
            me = instaloader.Profile.own_profile(bot.context)
            session_username = me.username
        else:
            session_username = None

        print(f"\nSession user:\t\t{session_username or '<anonymous>'}")
        print(f"\nUsername:\t\t{state.insta_username}")
        print(f"User ID:\t\t{state.insta_userid}")
        print(f"URL:\t\t\thttps://www.instagram.com/{state.insta_username}/")
        print(f"\nProfile:\t\t{'public' if not state.is_private else 'private'}")
        print(f"Can view all contents:\t{'Yes' if state.can_view else 'No'}")
        print(f"\nPosts:\t\t\t{state.posts_count}")
        if not config.skip_session and state.can_view:
            print(f"Reels:\t\t\t{state.reels_count}")
        print(f"\nFollowers:\t\t{state.followers_count}")
        print(f"Followings:\t\t{state.followings_count}")
        if bot.context.is_logged_in:
            print(f"\nStory available:\t{state.has_story}")
        print(f"\nBio:\n\n{state.bio}\n")
        print_cur_ts(local_timezone, config.horizontal_line, "Timestamp:\t\t")

        # Download initial profile picture
        if config.detect_changed_profile_pic:
            try:
                _detect_profile_pic_change(state, 0, False, initial=True)
            except Exception as e:
                print(f"* Error processing initial profile picture: {e}")

        print("─" * config.horizontal_line)
        state.initialized = True

    except Exception as e:
        print(f"* Error initializing user {username}: {type(e).__name__}: {e}")
        state.error = str(e)

    return state


def _detect_profile_pic_change(
    state: UserState,
    sleep_time: int,
    send_notification: bool,
    initial: bool = False,
) -> bool:
    """Detect if user's profile picture has changed.

    Args:
        state: UserState instance
        sleep_time: Current sleep interval
        send_notification: Whether to send notification
        initial: Whether this is initial download

    Returns:
        True if changed, False otherwise
    """
    config = state.config
    username = state.username
    local_tz = state.local_timezone

    profile_pic_path = get_image_path(username)
    profile_pic_tmp = get_image_path(username, "_tmp")
    profile_pic_old = get_image_path(username, "_old")

    # Download current profile pic to tmp
    if not save_pic_video(state.profile_image_url, str(profile_pic_tmp), config.user_agent):
        return False

    if initial:
        # First run - just save and return
        if not profile_pic_path.exists():
            profile_pic_tmp.rename(profile_pic_path)
            print(f"* Profile picture saved to '{profile_pic_path}'")
        return False

    # Compare with existing
    if not profile_pic_path.exists():
        profile_pic_tmp.rename(profile_pic_path)
        return False

    if compare_images(str(profile_pic_tmp), str(profile_pic_path)):
        # No change
        profile_pic_tmp.unlink(missing_ok=True)
        return False

    # Profile pic changed
    print(f"* Profile picture changed for user {username}\n")

    # Archive old pic with timestamp
    profile_pic_path.rename(profile_pic_old)
    profile_pic_tmp.rename(profile_pic_path)

    if send_notification and config.has_smtp_credentials():
        subject = f"Instagram user {username} profile picture has changed!"
        body = f"Profile picture changed for user {username}\n\n"
        body += f"Check interval: {display_time(sleep_time)} "
        body += f"({get_range_of_dates_from_tss(int(time.time()) - sleep_time, int(time.time()), local_tz, short=True)})"
        body += get_cur_ts(local_tz, "\nTimestamp: ")

        print(f"Sending email notification to {config.receiver_email}\n")
        send_email(config, subject, body)

    print(f"Check interval:\t\t{display_time(sleep_time)}")
    print_cur_ts(local_tz, config.horizontal_line, "Timestamp:\t\t")

    return True


def check_followings_changes(
    state: UserState,
    sleep_time: int,
) -> None:
    """Check for followings changes and send notifications.

    Args:
        state: UserState instance
        sleep_time: Current sleep interval
    """
    config = state.config
    local_tz = state.local_timezone
    signal_state = get_signal_state()

    if state.followings_count == state.followings_count_old:
        return

    # Followings count changed
    added = set(state.followings) - set(state.followings_old)
    removed = set(state.followings_old) - set(state.followings)

    if added or removed:
        print(f"* Followings changed for {state.username}:")
        if added:
            print(f"  Started following: {', '.join(added)}")
        if removed:
            print(f"  Unfollowed: {', '.join(removed)}")
        print()

        # Send notification
        status_notif = signal_state.status_notification if signal_state else config.status_notification
        if status_notif and config.has_smtp_credentials():
            subject = f"Instagram user {state.username} followings changed!"
            body = f"Followings changed for {state.username}\n"
            if added:
                body += f"Started following: {', '.join(added)}\n"
            if removed:
                body += f"Unfollowed: {', '.join(removed)}\n"
            body += f"\nCheck interval: {display_time(sleep_time)}"
            body += get_cur_ts(local_tz, "\nTimestamp: ")

            print(f"Sending email notification to {config.receiver_email}\n")
            send_email(config, subject, body)

        # Post to X
        if status_notif and config.x_notification and config.has_x_credentials():
            tweet = format_follow_tweet(
                state.username,
                state.full_name,
                list(added),
                list(removed),
            )

            # Generate profile card
            card_path = None
            if config.detect_changed_profile_pic:
                profile_pic = get_image_path(state.username)
                if profile_pic.exists():
                    from .persistence import get_profile_card_path
                    card_path = str(get_profile_card_path(state.username))
                    generate_profile_card(
                        state.username,
                        state.full_name,
                        state.followers_count,
                        state.followings_count,
                        str(profile_pic),
                        card_path,
                    )

            print("Posting to X...\n")
            post_to_x(tweet, card_path or "", config=config)

    # Update old values
    state.followings_count_old = state.followings_count
    state.followings_old = state.followings.copy()

    # Save to file
    save_followings(state.username, state.followings_count, state.followings)


def check_user_iteration(state: UserState, sleep_time: int) -> None:
    """Perform one check iteration for a user.

    Args:
        state: UserState instance
        sleep_time: Time since last check
    """
    config = state.config
    local_tz = state.local_timezone
    signal_state = get_signal_state()
    status_notif = signal_state.status_notification if signal_state else config.status_notification

    try:
        profile = get_profile(state.bot, state.username)
        time.sleep(config.next_operation_delay)

        # Update current values
        state.followers_count = profile.followers
        state.followings_count = profile.followees
        state.bio = profile.biography
        state.is_private = profile.is_private
        state.followed_by_viewer = profile.followed_by_viewer
        state.can_view = (not profile.is_private) or profile.followed_by_viewer
        state.posts_count = profile.mediacount
        state.profile_image_url = profile.profile_pic_url_no_iphone

        # Check bio change
        if state.bio != state.bio_old:
            print(f"* Bio changed for user {state.username}:\n")
            print(f"Old bio:\n{state.bio_old}\n")
            print(f"New bio:\n{state.bio}\n")

            if status_notif and config.has_smtp_credentials():
                subject = f"Instagram user {state.username} bio has changed!"
                body = f"Bio changed for {state.username}\n\nOld: {state.bio_old}\n\nNew: {state.bio}"
                body += get_cur_ts(local_tz, "\nTimestamp: ")
                send_email(config, subject, body)

            state.bio_old = state.bio

        # Check profile picture change
        if config.detect_changed_profile_pic:
            _detect_profile_pic_change(state, sleep_time, status_notif)

        # Check posts count
        if state.posts_count != state.posts_count_old:
            print(f"* Posts count changed for {state.username}: {state.posts_count_old} -> {state.posts_count}\n")
            state.posts_count_old = state.posts_count

        # Check followings if we have lists
        if state.followings and not config.skip_followings:
            try:
                followings = [followee.username for followee in profile.get_followees()]
                state.followings = followings
                check_followings_changes(state, sleep_time)
            except Exception as e:
                print(f"* Error fetching followings: {e}")

    except Exception as e:
        print(f"* Error checking user {state.username}: {type(e).__name__}: {e}")


def monitor_users(config: Config) -> None:
    """Main monitoring loop for multiple users.

    Args:
        config: Config instance with target usernames
    """
    # Ensure data directories exist
    ensure_data_dirs()

    # Get local timezone
    local_timezone = get_local_timezone(config)
    if not local_timezone:
        print("* Error: Could not determine timezone")
        sys.exit(1)

    # Register signal handlers
    signal_state = register_signal_handlers(config, local_timezone)

    print("Initializing Instagram session...")

    try:
        bot = init_bot(config)
    except Exception as e:
        print(f"* Error initializing Instagram session: {type(e).__name__}: {e}")
        sys.exit(1)

    # Initialize state for each user
    user_states: List[UserState] = []
    for username in config.target_usernames:
        state = init_user_state(username, bot, config, local_timezone)
        user_states.append(state)

        # Delay between users to avoid rate limiting
        if len(config.target_usernames) > 1:
            time.sleep(5)

    # Filter to successfully initialized users
    active_states = [s for s in user_states if s.initialized]

    if not active_states:
        print("* No users successfully initialized, exiting")
        sys.exit(1)

    print(f"\n* Monitoring {len(active_states)} user(s)...")

    # Main monitoring loop
    liveness_counter = 0
    liveness_interval = config.liveness_check_interval // config.check_interval if config.liveness_check_interval else 0

    while True:
        # Get current check interval from signal state
        check_interval = signal_state.check_interval

        for state in active_states:
            sleep_time = randomize_number(
                check_interval,
                config.random_sleep_diff_low,
                config.random_sleep_diff_high,
            )

            print(f"\n* Checking user {state.username}...")
            check_user_iteration(state, sleep_time)

            # Sleep between users
            if len(active_states) > 1:
                time.sleep(config.next_operation_delay * 2)

        # Liveness check
        liveness_counter += 1
        if liveness_interval and liveness_counter >= liveness_interval:
            print(f"\n* Liveness check - still monitoring {len(active_states)} user(s)")
            print_cur_ts(local_timezone, config.horizontal_line, "Timestamp:\t\t")
            liveness_counter = 0

        # Human simulation
        if config.be_human and not config.skip_session:
            simulate_human_actions(
                bot,
                check_interval,
                config,
                lambda: print_cur_ts(local_timezone, config.horizontal_line, "\nTimestamp:\t\t"),
            )

        # Sleep until next check
        sleep_time = randomize_number(
            check_interval,
            config.random_sleep_diff_low,
            config.random_sleep_diff_high,
        )

        print(f"\n* Sleeping for {display_time(sleep_time)}...")
        time.sleep(sleep_time)
