#!/usr/bin/env python3
"""
Standalone script to post Instagram profile updates to X/Twitter.
Reads cached profile data from instagram_*_followings.json files.

Usage:
    python post_to_x.py <username> [--added user1,user2] [--removed user3]
    python post_to_x.py <username> --from-diff old.json new.json

Examples:
    # Post a follow event
    python post_to_x.py sinemkobal --added kademorgtr

    # Diff two snapshots and post changes
    python post_to_x.py sinemkobal --from-diff old_followings.json new_followings.json

    # Dry run to preview tweet
    python post_to_x.py sinemkobal --added user1,user2 --dry-run
"""

import argparse
import json
import os
import sys

from src.config import load_env_config
from src.x_poster import post_to_x, format_follow_tweet
from src.profile_card import generate_profile_card


def load_profile_data(username):
    """Load cached profile data for a username.

    Args:
        username: Instagram username

    Returns:
        Dict with username, full_name, followers_count, followings_count,
        followings list, and profile_pic path.
    """
    followings_file = f"instagram_{username}_followings.json"
    profile_pic = f"instagram_{username}_profile_pic.jpeg"

    data = {
        "username": username,
        "full_name": "",
        "followers_count": 0,
        "followings_count": 0,
        "followings": [],
        "profile_pic": profile_pic if os.path.exists(profile_pic) else None,
    }

    if os.path.exists(followings_file):
        try:
            with open(followings_file, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, list) and len(content) >= 2:
                    data["followings_count"] = content[0]
                    data["followings"] = content[1]
        except (json.JSONDecodeError, IOError) as e:
            print(f"* Warning: Could not load {followings_file}: {e}")

    return data


def diff_followings(old_file, new_file):
    """Compare two followings JSON files and return added/removed.

    Args:
        old_file: Path to older followings JSON
        new_file: Path to newer followings JSON

    Returns:
        Tuple of (added_list, removed_list)
    """
    with open(old_file, "r", encoding="utf-8") as f:
        old_data = json.load(f)
    with open(new_file, "r", encoding="utf-8") as f:
        new_data = json.load(f)

    old_set = set(old_data[1]) if isinstance(old_data, list) and len(old_data) > 1 else set()
    new_set = set(new_data[1]) if isinstance(new_data, list) and len(new_data) > 1 else set()

    return list(new_set - old_set), list(old_set - new_set)


def main():
    parser = argparse.ArgumentParser(
        description="Post Instagram profile updates to X/Twitter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s sinemkobal --added kademorgtr
  %(prog)s sinemkobal --from-diff old.json new.json
  %(prog)s sinemkobal --added user1,user2 --dry-run
        """,
    )
    parser.add_argument("username", help="Instagram username")
    parser.add_argument(
        "--added",
        metavar="USERS",
        help="Comma-separated list of newly followed users",
    )
    parser.add_argument(
        "--removed",
        metavar="USERS",
        help="Comma-separated list of unfollowed users",
    )
    parser.add_argument(
        "--from-diff",
        nargs=2,
        metavar=("OLD", "NEW"),
        help="Compute diff from two followings JSON files",
    )
    parser.add_argument(
        "--env-file",
        default=".env.local",
        help="Path to .env file (default: .env.local)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print tweet without posting",
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="Post without profile card image",
    )

    args = parser.parse_args()

    # Load config
    load_env_config(args.env_file)

    # Load profile data
    profile = load_profile_data(args.username)

    # Determine added/removed
    if args.from_diff:
        if not os.path.exists(args.from_diff[0]):
            print(f"Error: File not found: {args.from_diff[0]}")
            return 1
        if not os.path.exists(args.from_diff[1]):
            print(f"Error: File not found: {args.from_diff[1]}")
            return 1
        added, removed = diff_followings(args.from_diff[0], args.from_diff[1])
    else:
        added = [u.strip() for u in args.added.split(",")] if args.added else []
        removed = [u.strip() for u in args.removed.split(",")] if args.removed else []

    if not added and not removed:
        print("No follow changes to post")
        return 0

    # Generate profile card
    card_path = None
    if not args.no_image:
        card_path = f"/tmp/instagram_{args.username}_card.jpeg"
        result = generate_profile_card(
            args.username,
            profile["full_name"],
            profile["followers_count"],
            profile["followings_count"],
            profile["profile_pic"],
            card_path,
        )
        if result:
            print(f"* Generated profile card: {card_path}")
        else:
            card_path = None

    # Format tweet
    tweet_text = format_follow_tweet(
        args.username, profile["full_name"], added, removed
    )

    print(f"\nTweet ({len(tweet_text)} chars):")
    print("-" * 40)
    print(tweet_text)
    print("-" * 40)
    print()

    if args.dry_run:
        print("(dry run - not posting)")
        return 0

    # Post to X
    return post_to_x(tweet_text, card_path or "")


if __name__ == "__main__":
    sys.exit(main())
