#!/usr/bin/env python3
"""
Test script for profile card image generation.

Usage:
    python test_image.py <username> [--output FILE]
    python test_image.py --demo

Examples:
    python test_image.py --demo
    python test_image.py mcdavid97
    python test_image.py sinemkobal --name "Sinem Kobal" --followers 6100000 --following 997
"""

import argparse
import os
import sys

from src.profile_card import generate_profile_card


def load_profile_pic(username):
    """Find profile picture for username."""
    pic_path = f"instagram_{username}_profile_pic.jpeg"
    return pic_path if os.path.exists(pic_path) else None


def main():
    parser = argparse.ArgumentParser(
        description="Test profile card image generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --demo
  %(prog)s mcdavid97
  %(prog)s sinemkobal --name "Sinem Kobal" --followers 6100000 --following 997
  %(prog)s mcdavid97 --open
        """,
    )
    parser.add_argument("username", nargs="?", help="Instagram username")
    parser.add_argument(
        "--output", "-o", help="Output file path (default: /tmp/instagram_<user>_card.jpeg)"
    )
    parser.add_argument(
        "--demo", action="store_true", help="Generate demo card with sample data"
    )
    parser.add_argument(
        "--followers", type=int, default=1000000, help="Follower count (default: 1000000)"
    )
    parser.add_argument(
        "--following", type=int, default=500, help="Following count (default: 500)"
    )
    parser.add_argument("--name", help="Display name")
    parser.add_argument("--category", help="Category label (e.g., 'Artist', 'Musician')")
    parser.add_argument(
        "--open", action="store_true", help="Open image after generation (macOS)"
    )

    args = parser.parse_args()

    if args.demo:
        username = "demo_user"
        display_name = "Demo User"
        followers = 1234567
        following = 890
        profile_pic = None
        category = "Demo Category"
    elif args.username:
        username = args.username
        display_name = args.name or ""
        followers = args.followers
        following = args.following
        profile_pic = load_profile_pic(username)
        category = args.category or ""
    else:
        parser.print_help()
        return 1

    output_path = args.output or f"instagram_{username}_card.jpeg"

    print(f"Generating profile card for: {username}")
    print(f"  Display name: {display_name or '(none)'}")
    print(f"  Followers: {followers:,}")
    print(f"  Following: {following:,}")
    print(f"  Category: {category or '(none)'}")
    print(f"  Profile pic: {profile_pic or '(none)'}")
    print(f"  Output: {output_path}")

    result = generate_profile_card(
        username, display_name, followers, following, profile_pic, output_path, category
    )

    if result:
        print(f"\n✓ Generated: {result}")
        if args.open:
            os.system(f"open '{result}'")
        return 0
    else:
        print("\n✗ Failed to generate image")
        return 1


if __name__ == "__main__":
    sys.exit(main())
