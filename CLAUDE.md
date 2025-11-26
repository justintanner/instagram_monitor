# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Instagram Monitor is an OSINT tool for real-time monitoring of Instagram users' activities and profile changes. It uses the instaloader library for Instagram API access.

## Commands

### Installation
```sh
pip install -r requirements.txt
```

### Running
```sh
# Mode 1: Anonymous (no login) - limited features
python3 start.py <target_username>

# Mode 2: With session login - full features
python3 start.py -u <your_username> <target_username>

# Import Firefox session (recommended for mode 2)
python3 start.py --import-firefox-session

# Send test email
python3 start.py --send-test-email

# Send test X post
python3 start.py --send-test-x
```

### Docker
```sh
# Build the image
docker build -t instagram-monitor .

# Run in mode 1 (anonymous)
docker run -v $(pwd)/data:/data instagram-monitor <target_username>

# Run in mode 2 (with session)
docker run -v $(pwd)/data:/data \
  -e SESSION_PASSWORD="your_password" \
  instagram-monitor -u <your_username> <target_username>
```

## Architecture

**Modular design**: The application is organized into modules in `src/`:

```
start.py                    # Entry point (CLI parsing)
src/
├── __init__.py            # Package exports
├── config.py              # Configuration dataclass, .env loading
├── client.py              # Instagram API wrapper (instaloader)
├── monitor.py             # Main monitoring loop, user state
├── notifications.py       # Email + X/Twitter notifications
├── profile_card.py        # Profile card image generation
├── persistence.py         # File I/O, JSON, CSV operations
├── time_utils.py          # Date/time utilities
├── logger.py              # Logger class, utilities
└── signals.py             # Signal handlers
data/                       # All output files
├── logs/                  # Log files
├── images/                # Profile pictures, media
└── *.json                 # Followers/followings lists
```

**Configuration**: Settings loaded from `.env.local` file via python-dotenv. Copy `.env.example` to `.env.local` and configure.

**Two operation modes**:
1. **Mode 1 (Anonymous)**: No login required, limited to basic profile data and public posts
2. **Mode 2 (Session login)**: Full access including followers/followings lists, stories, reels

**Key dependencies**:
- `instaloader`: Core Instagram API interaction
- `requests`: HTTP requests for profile pictures, connectivity checks
- `pytz`/`tzlocal`: Timezone handling
- `python-dotenv`: Secret management via .env files
- `tweepy`: X/Twitter posting (optional)
- `Pillow`: Profile card generation (optional)

**Output files** (all in `data/` directory):
- `data/logs/monitor_<username>.log` - Activity log
- `data/<username>_followings.json` / `_followers.json` - Cached lists
- `data/images/<username>_profile_pic*.jpeg` - Profile pictures
- `data/images/<username>_post/reel/story_*.jpeg/mp4` - Downloaded media

## Code Style

- Functional style preferred over OOP
- Configuration via dataclass loaded from .env
- Signal handlers for runtime control (USR1, USR2, TRAP, ABRT, HUP)
- Python 3.9+ required
- Type hints throughout
