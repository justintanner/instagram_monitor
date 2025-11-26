#!/usr/bin/env python3
"""Simple Instagram profile image downloader."""

import os
import sys
import re
import shutil
import requests
import instaloader
from itertools import islice


def extract_username(url: str) -> str:
    """Extract username from Instagram URL or return as-is if already username."""
    match = re.search(r'instagram\.com/([^/?]+)', url)
    return match.group(1) if match else url.strip('/')


def download_image(url: str, filename: str) -> bool:
    """Download image from URL to local file."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15,
            stream=True,
        )
        response.raise_for_status()
        with open(filename, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        return True
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
        return False


def main(profile_url: str, num_posts: int = 5, output_dir: str = "downloads") -> None:
    """Download profile pic and recent posts from Instagram profile."""
    username = extract_username(profile_url)
    print(f"Downloading images for: {username}")

    # Create output folder
    folder = os.path.join(output_dir, username)
    os.makedirs(folder, exist_ok=True)

    bot = instaloader.Instaloader(quiet=True)

    try:
        profile = instaloader.Profile.from_username(bot.context, username)
    except Exception as e:
        print(f"Error: Could not load profile '{username}': {e}")
        sys.exit(1)

    # Download profile picture
    pic_url = profile.profile_pic_url_no_iphone
    pic_file = os.path.join(folder, f"{username}_profile.jpg")
    if download_image(pic_url, pic_file):
        print(f"Saved: {pic_file}")

    # Download recent post images
    for i, post in enumerate(islice(profile.get_posts(), num_posts), 1):
        post_file = os.path.join(folder, f"{username}_post_{i}.jpg")
        if download_image(post.url, post_file):
            print(f"Saved: {post_file}")

    print("Done.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 ig_downloader.py <instagram_url_or_username> [num_posts]")
        print("Example: python3 ig_downloader.py https://instagram.com/mcdavid97 5")
        sys.exit(1)

    url = sys.argv[1]
    num = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    main(url, num)
