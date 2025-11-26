"""Instagram API client wrapper using instaloader."""

import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from functools import wraps
from glob import glob
from itertools import islice
from os.path import basename, dirname, expanduser
from platform import system
from sqlite3 import OperationalError, connect
from typing import Any, Callable, List, Optional, Tuple

import instaloader
import requests
from instaloader.exceptions import PrivateProfileNotFollowedException

from .config import Config


def get_random_user_agent() -> str:
    """Generate a random desktop browser user agent string.

    Returns:
        User agent string
    """
    browser = random.choice(["chrome", "firefox", "edge", "safari"])

    if browser == "chrome":
        os_choice = random.choice(["mac", "windows"])
        if os_choice == "mac":
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(4, 9)}) "
                f"AppleWebKit/{random.randrange(530, 537)}.{random.randrange(30, 37)} (KHTML, like Gecko) "
                f"Chrome/{random.randrange(80, 105)}.0.{random.randrange(3000, 4500)}.{random.randrange(60, 125)} "
                f"Safari/{random.randrange(530, 537)}.{random.randrange(30, 36)}"
            )
        else:
            chrome_version = random.randint(80, 105)
            build = random.randint(3000, 4500)
            patch = random.randint(60, 125)
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{chrome_version}.0.{build}.{patch} Safari/537.36"
            )

    elif browser == "firefox":
        os_choice = random.choice(["windows", "mac", "linux"])
        version = random.randint(90, 110)
        if os_choice == "windows":
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )
        elif os_choice == "mac":
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(0, 10)}; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )
        else:
            return (
                f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}.0) "
                f"Gecko/20100101 Firefox/{version}.0"
            )

    elif browser == "edge":
        os_choice = random.choice(["windows", "mac"])
        chrome_version = random.randint(80, 105)
        build = random.randint(3000, 4500)
        patch = random.randint(60, 125)
        version_str = f"{chrome_version}.0.{build}.{patch}"
        if os_choice == "windows":
            return (
                f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{version_str} Safari/537.36 Edg/{version_str}"
            )
        else:
            return (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{random.randrange(11, 15)}_{random.randrange(0, 10)}) "
                f"AppleWebKit/605.1.15 (KHTML, like Gecko) "
                f"Version/{random.randint(13, 16)}.0 Safari/605.1.15 Edg/{version_str}"
            )

    elif browser == "safari":
        mac_major = random.randrange(11, 16)
        mac_minor = random.randrange(0, 10)
        webkit_major = random.randint(600, 610)
        webkit_minor = random.randint(1, 20)
        webkit_patch = random.randint(1, 20)
        safari_version = random.randint(13, 16)
        return (
            f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{mac_major}_{mac_minor}) "
            f"AppleWebKit/{webkit_major}.{webkit_minor}.{webkit_patch} (KHTML, like Gecko) "
            f"Version/{safari_version}.0 Safari/{webkit_major}.{webkit_minor}.{webkit_patch}"
        )

    return ""


def get_random_mobile_user_agent() -> str:
    """Generate a random mobile (iPhone/iPad) user agent string.

    Returns:
        Mobile user agent string
    """
    app_major = random.randint(240, 300)
    app_minor = random.randint(0, 9)
    app_patch = random.randint(0, 9)
    app_revision = random.randint(100, 999)

    if random.choice([True, False]):
        device = "iPhone"
        model, (width, height) = random.choice([
            ("10,3", (1125, 2436)),
            ("11,2", (1125, 2436)),
            ("12,5", (1242, 2688)),
            ("13,4", (1284, 2778)),
            ("14,2", (1179, 2532)),
            ("14,4", (1080, 2340)),
            ("15,2", (1170, 2532)),
            ("15,3", (1179, 2556)),
            ("16,1", (1290, 2796)),
        ])
    else:
        device = "iPad"
        model, (width, height) = random.choice([
            ("7,11", (1620, 2160)),
            ("13,4", (1668, 2388)),
            ("13,8", (2048, 2732)),
            ("14,5", (2360, 1640)),
            ("15,1", (2048, 2732)),
            ("15,8", (1668, 2388)),
        ])

    os_major = random.randint(12, 17)
    os_minor = random.randint(0, 5)
    language = "en_US"
    locale = "en-US"
    scale = random.choice([2.00, 3.00])
    device_id = random.randint(10**14, 10**15 - 1)

    return (
        f"Instagram {app_major}.{app_minor}.{app_patch}.{app_revision} "
        f"({device}{model}; iOS {os_major}_{os_minor}; {language}; {locale}; "
        f"scale={scale:.2f}; {width}x{height}; {device_id}) AppleWebKit/420+"
    )


def wrap_request_with_jitter(orig_request: Callable, jitter_verbose: bool = False) -> Callable:
    """Wrap HTTP request method with jitter and back-off.

    Args:
        orig_request: Original request method
        jitter_verbose: Enable verbose logging

    Returns:
        Wrapped request method
    """
    @wraps(orig_request)
    def wrapper(*args, **kwargs):
        method = kwargs.get("method") or (args[1] if len(args) > 1 else None)
        url = kwargs.get("url") or (args[2] if len(args) > 2 else None)
        if jitter_verbose:
            print(f"[WRAP-REQ] {method} {url}")
        time.sleep(random.uniform(0.8, 3.0))

        attempt = 0
        backoff = 60
        while True:
            resp = orig_request(*args, **kwargs)
            if resp.status_code in (429, 400) and "checkpoint" in resp.text:
                attempt += 1
                if attempt > 3:
                    raise instaloader.exceptions.QueryReturnedNotFoundException(
                        "Giving up after multiple 429/checkpoint"
                    )
                wait = backoff + random.uniform(0, 30)
                if jitter_verbose:
                    print(f"* Back-off {wait:.0f}s after {resp.status_code}")
                time.sleep(wait)
                backoff *= 2
                continue
            return resp

    return wrapper


def wrap_send_with_jitter(orig_send: Callable, jitter_verbose: bool = False) -> Callable:
    """Wrap HTTP send method with jitter.

    Args:
        orig_send: Original send method
        jitter_verbose: Enable verbose logging

    Returns:
        Wrapped send method
    """
    @wraps(orig_send)
    def wrapper(*args, **kwargs):
        req_obj = args[1] if len(args) > 1 else kwargs.get("request")
        method = getattr(req_obj, "method", None)
        url = getattr(req_obj, "url", None)
        if jitter_verbose:
            print(f"[WRAP-SEND] {method} {url}")
        time.sleep(random.uniform(0.8, 3.0))
        return orig_send(*args, **kwargs)

    return wrapper


def probability_for_cycle(sleep_seconds: int, daily_human_hits: int) -> float:
    """Calculate probability of executing human action for this cycle.

    Args:
        sleep_seconds: Sleep interval in seconds
        daily_human_hits: Target number of actions per day

    Returns:
        Probability (0.0 to 1.0)
    """
    return min(1.0, daily_human_hits * sleep_seconds / 86_400)


def simulate_human_actions(
    bot: instaloader.Instaloader,
    sleep_seconds: int,
    config: Config,
    print_ts_func: Optional[Callable] = None,
) -> None:
    """Perform random actions to simulate human behavior.

    Args:
        bot: Instaloader instance
        sleep_seconds: Current sleep interval
        config: Config instance
        print_ts_func: Optional function to print timestamp
    """
    ctx = bot.context
    prob = probability_for_cycle(sleep_seconds, config.daily_human_hits)
    verbose = config.be_human_verbose

    if verbose:
        print("─" * config.horizontal_line)
        print("* BeHuman: simulation start")

    # Explore feed
    if ctx.is_logged_in and random.random() < prob:
        try:
            posts = bot.get_explore_posts()
            next(posts)
            if verbose:
                print("* BeHuman #1: explore feed peek OK")
            time.sleep(random.uniform(2, 6))
        except Exception as e:
            if verbose:
                print(f"* BeHuman #1 error: explore peek failed ({e})")

    # View own profile
    if ctx.is_logged_in and random.random() < prob:
        try:
            instaloader.Profile.own_profile(ctx)
            if verbose:
                print("* BeHuman #2: viewed own profile OK")
            time.sleep(random.uniform(1, 4))
        except Exception as e:
            if verbose:
                print(f"* BeHuman #2 error: cannot view own profile: {e}")

    # Browse random hashtag
    if random.random() < prob / 2 and config.my_hashtags:
        tag = random.choice(config.my_hashtags)
        try:
            posts = bot.get_hashtag_posts(tag)
            next(posts)
            if verbose:
                print(f"* BeHuman #3: browsed one post from #{tag} OK")
            time.sleep(random.uniform(2, 5))
        except StopIteration:
            if verbose:
                print(f"* BeHuman #3 warning: no posts for #{tag}")
        except Exception as e:
            if verbose:
                print(f"* BeHuman #3 error: cannot browse #{tag}: {e}")

    # Visit random followee
    if ctx.is_logged_in and random.random() < prob / 2:
        try:
            me = instaloader.Profile.own_profile(ctx)
            followees = list(me.get_followees())
            if not followees and verbose:
                print("* BeHuman #4 warning: you follow 0 accounts, skipping visit")
            else:
                someone = random.choice(followees)
                instaloader.Profile.from_username(ctx, someone.username)
                if verbose:
                    print(f"* BeHuman #4: visited followee {someone.username} OK")
                time.sleep(random.uniform(2, 5))
        except Exception as e:
            if verbose:
                print(f"* BeHuman #4 error: cannot visit followee: {e}")

    if verbose:
        print("* BeHuman: simulation stop")
        if print_ts_func:
            print_ts_func()


def get_firefox_cookiefile(config: Config) -> str:
    """Find or prompt for Firefox cookies.sqlite file.

    Args:
        config: Config instance

    Returns:
        Path to cookies.sqlite file

    Raises:
        SystemExit: If no cookie file found
    """
    default_cookiefile = {
        "Windows": config.firefox_windows_cookie,
        "Darwin": config.firefox_macos_cookie,
    }.get(system(), config.firefox_linux_cookie)

    cookiefiles = glob(expanduser(default_cookiefile))

    if not cookiefiles:
        raise SystemExit("No Firefox cookies.sqlite file found, use -c COOKIEFILE flag")

    if len(cookiefiles) == 1:
        return cookiefiles[0]

    print("Multiple Firefox profiles found:")
    for idx, path in enumerate(cookiefiles, start=1):
        profile = basename(dirname(path))
        print(f"  {idx}) {profile}  -  {path}")

    try:
        choice = int(input("Select profile number (0 to exit): "))
        if choice == 0:
            raise SystemExit("No profile selected, aborting ...")
        cookiefile = cookiefiles[choice - 1]
    except (ValueError, IndexError):
        raise SystemExit("Invalid profile selection !")
    return cookiefile


def import_firefox_session(cookiefile: str, sessionfile: Optional[str] = None) -> None:
    """Import Instagram session from Firefox cookies.

    Args:
        cookiefile: Path to Firefox cookies.sqlite
        sessionfile: Optional path to save session file

    Raises:
        SystemExit: If import fails
    """
    print(f"Using cookies from '{cookiefile}' file\n")

    try:
        conn = connect(f"file:{cookiefile}?immutable=1", uri=True)

        try:
            cookie_iter = conn.execute(
                "SELECT name, value FROM moz_cookies WHERE baseDomain='instagram.com'"
            )
        except OperationalError:
            cookie_iter = conn.execute(
                "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
            )

        cookie_dict = dict(cookie_iter)

    except sqlite3.DatabaseError:
        raise SystemExit(f"Error: '{cookiefile}' is not a valid Firefox cookies.sqlite file")

    loader = instaloader.Instaloader(max_connection_attempts=1)
    loader.context._session.cookies.update(cookie_dict)
    username = loader.test_login()

    if not username:
        raise SystemExit("Not logged in - are you logged in successfully in Firefox?")

    print(f"Imported session cookies for {username}")

    loader.context.username = username

    if sessionfile:
        loader.save_session_to_file(sessionfile)
    else:
        loader.save_session_to_file()


def init_bot(config: Config) -> instaloader.Instaloader:
    """Initialize instaloader bot instance.

    Args:
        config: Config instance

    Returns:
        Configured Instaloader instance
    """
    # Apply jitter wrappers if enabled
    if config.enable_jitter:
        requests.Session.request = wrap_request_with_jitter(
            requests.Session.request, config.jitter_verbose
        )
        requests.Session.send = wrap_send_with_jitter(
            requests.Session.send, config.jitter_verbose
        )

    user_agent = config.user_agent or get_random_user_agent()
    user_agent_mobile = config.user_agent_mobile or get_random_mobile_user_agent()

    bot = instaloader.Instaloader(user_agent=user_agent, iphone_support=True, quiet=True)
    ctx = bot.context

    if not config.skip_session and config.session_username:
        if config.session_password:
            try:
                bot.load_session_from_file(config.session_username)
            except FileNotFoundError:
                bot.login(config.session_username, config.session_password)
                bot.save_session_to_file()
            except instaloader.exceptions.BadCredentialsException:
                bot.login(config.session_username, config.session_password)
                bot.save_session_to_file()
        else:
            try:
                bot.load_session_from_file(config.session_username)
            except FileNotFoundError:
                print(
                    "* Error: No Instagram session file found, please run "
                    "'instaloader -l SESSION_USERNAME' to create one"
                )
                sys.exit(1)

    # Mobile user agent patch
    _apply_mobile_user_agent(ctx, user_agent_mobile)

    return bot


def _apply_mobile_user_agent(ctx: Any, user_agent_mobile: str) -> None:
    """Apply mobile user agent to instaloader context.

    Args:
        ctx: Instaloader context
        user_agent_mobile: Mobile user agent string
    """
    patched = False
    try:
        for attr in ("iphone_headers", "_iphone_headers"):
            if hasattr(ctx, attr):
                getattr(ctx, attr)["User-Agent"] = user_agent_mobile
                patched = True
                break

        if not patched:
            if hasattr(ctx, "get_iphone_json"):
                orig_get_iphone_json = ctx.get_iphone_json

                def _get_iphone_json(path, params, **kwargs):
                    if "_extra_headers" in kwargs:
                        kwargs["_extra_headers"]["User-Agent"] = user_agent_mobile
                    else:
                        kwargs["_extra_headers"] = {"User-Agent": user_agent_mobile}
                    return orig_get_iphone_json(path, params, **kwargs)

                ctx.get_iphone_json = _get_iphone_json
            else:
                print(
                    "* Warning: Could not apply custom mobile user-agent patch "
                    "(missing header attributes or get_iphone_json method)!"
                )
                print("* Proceeding with the default Instaloader mobile user-agent")
    except Exception as e:
        print(f"* Warning: Could not apply custom mobile user-agent patch: {e}")
        print("* Proceeding with the default Instaloader mobile user-agent")


def get_profile(bot: instaloader.Instaloader, username: str) -> instaloader.Profile:
    """Get Instagram profile by username.

    Args:
        bot: Instaloader instance
        username: Instagram username

    Returns:
        Profile object
    """
    return instaloader.Profile.from_username(bot.context, username)


def latest_post_reel(
    username: str, bot: instaloader.Instaloader
) -> Optional[Tuple[instaloader.Post, str]]:
    """Get the most recent post or reel for a user.

    Args:
        username: Instagram username
        bot: Instaloader instance

    Returns:
        Tuple of (Post, source_type) or None
    """
    profile = instaloader.Profile.from_username(bot.context, username)

    # Max 3 pinned posts + the latest one
    posts = [(p, "post") for p in islice(profile.get_posts(), 4)]
    reels = [(r, "reel") for r in islice(profile.get_reels(), 4)]

    candidates = posts + reels

    if not candidates:
        return None

    latest, source = max(candidates, key=lambda pair: pair[0].date_utc)
    return latest, source


def latest_post_mobile(username: str, bot: instaloader.Instaloader) -> Optional[Tuple[Any, str]]:
    """Get latest post via mobile API (anonymous fallback).

    Args:
        username: Instagram username
        bot: Instaloader instance

    Returns:
        Tuple of (Post-like object, "post") or None
    """
    class P:
        date_utc: datetime
        likes: int
        comments: int
        caption: str
        pcaption: str
        tagged_users: List[Any]
        shortcode: str
        url: str
        video_url: Optional[str]
        mediaid: str

    data = bot.context.get_iphone_json(
        f"api/v1/users/web_profile_info/?username={username}", {}
    )
    edges = data["data"]["user"].get("edge_owner_to_timeline_media", {}).get("edges", [])

    if not edges:
        return None

    node = edges[0]["node"]

    p = P()
    p.mediaid = node.get("id", "")
    p.date_utc = datetime.fromtimestamp(node["taken_at_timestamp"], timezone.utc)
    p.likes = node["edge_liked_by"]["count"]
    p.comments = node["edge_media_to_comment"]["count"]
    p.caption = (
        node.get("edge_media_to_caption", {})
        .get("edges", [{}])[0]
        .get("node", {})
        .get("text", "")
    )
    p.pcaption = ""
    p.tagged_users = []
    p.shortcode = node["shortcode"]
    p.url = node.get("display_url", "")
    p.video_url = node.get("video_url")

    return p, "post"


def get_reels_count_mobile(username: str, bot: instaloader.Instaloader) -> int:
    """Get reel count via mobile API.

    Args:
        username: Instagram username
        bot: Instaloader instance

    Returns:
        Number of reels
    """
    profile = instaloader.Profile.from_username(bot.context, username)
    user_id = profile.userid

    ctx: Any = bot.context
    data = ctx.get_iphone_json(f"api/v1/users/{user_id}/info/", {})

    u = data.get("user", {})
    return u.get("reel_count") or u.get("total_clips_count", 0)


def get_total_reels_count(
    username: str, bot: instaloader.Instaloader, skip_session: bool = False
) -> int:
    """Get total reel count with fallback methods.

    Args:
        username: Instagram username
        bot: Instaloader instance
        skip_session: Whether session login is skipped

    Returns:
        Number of reels
    """
    # Try mobile API first
    if not skip_session:
        try:
            return get_reels_count_mobile(username, bot)
        except Exception:
            pass

    # Anonymous fallback: count reels (API intensive)
    try:
        profile = instaloader.Profile.from_username(bot.context, username)
        count = 0
        for _ in profile.get_reels():
            count += 1
        return count
    except PrivateProfileNotFollowedException:
        return 0


def get_post_location_mobile(
    last_post: instaloader.Post, bot: instaloader.Instaloader
) -> Optional[str]:
    """Get post location name via mobile API.

    Args:
        last_post: Post object
        bot: Instaloader instance

    Returns:
        Location name or None
    """
    if not bot.context.is_logged_in:
        return None

    media_id = getattr(last_post, "mediaid", None)
    if media_id is None:
        return None

    ctx: Any = bot.context
    try:
        data = ctx.get_iphone_json(f"api/v1/media/{media_id}/info/", {})
        items = data.get("items", [])
        if not items:
            return None
        media = items[0]
        loc_node = media.get("location")
        if isinstance(loc_node, dict):
            return loc_node.get("name")
    except Exception:
        return None

    return None


def get_real_reel_code(bot: instaloader.Instaloader, username: str) -> Optional[str]:
    """Get shortcode for user's latest reel via mobile API.

    Args:
        bot: Instaloader instance
        username: Instagram username

    Returns:
        Reel shortcode or None
    """
    try:
        ctx: Any = bot.context
        data = ctx.get_iphone_json(
            f"api/v1/users/web_profile_info/?username={username}", {}
        )
        user = data["data"]["user"]
        edges = user.get("edge_reels_media", {}).get("edges", [])
        if not edges:
            return None
        return edges[0]["node"].get("shortcode")
    except Exception:
        return None
