# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

instagram_monitor is an OSINT tool for real-time monitoring of Instagram users' activities and profile changes. It's a single-file Python CLI application (v1.8) that uses the instaloader library for Instagram API access.

## Commands

### Installation
```sh
pip install -r requirements.txt
# or install as package
pip install .
```

### Running
```sh
# Mode 1: Anonymous (no login) - limited features
python3 instagram_monitor.py <target_username>

# Mode 2: With session login - full features
python3 instagram_monitor.py -u <your_username> <target_username>

# Generate config template
python3 instagram_monitor.py --generate-config > instagram_monitor.conf

# Import Firefox session (recommended for mode 2)
python3 instagram_monitor.py --import-firefox-session

# Send test email
python3 instagram_monitor.py --send-test-email
```

### Building/Publishing
```sh
python -m build
```

### Docker
```sh
# Build the image
docker build -t instagram-monitor .

# Run in mode 1 (anonymous)
docker run -v $(pwd)/data:/data instagram-monitor <target_username>

# Run in mode 2 (with session) - pass secrets via environment
docker run -v $(pwd)/data:/data \
  -e SESSION_PASSWORD="your_password" \
  instagram-monitor -u <your_username> <target_username>

# Using docker-compose (edit docker-compose.yml first)
docker compose up -d
```

## Architecture

**Single-file design**: The entire application is in `instagram_monitor.py` (~3000+ lines). It follows functional/procedural Python with minimal OOP (only a Logger class for dual stdout/file output).

**Configuration**: Settings are defined in a CONFIG_BLOCK string at the top of the file, which is exec'd to set globals. External config can be loaded from `instagram_monitor.conf`.

**Two operation modes**:
1. **Mode 1 (Anonymous)**: No login required, limited to basic profile data and public posts
2. **Mode 2 (Session login)**: Full access including followers/followings lists, stories, reels

**Key dependencies**:
- `instaloader`: Core Instagram API interaction
- `requests`: HTTP requests for profile pictures, connectivity checks
- `pytz`/`tzlocal`: Timezone handling
- `python-dotenv`: Secret management via .env files

**Output files generated during runtime**:
- `instagram_monitor_<username>.log` - Activity log
- `instagram_<username>_followings.json` / `_followers.json` - Cached lists
- `instagram_<username>_profile_pic*.jpeg` - Profile pictures
- `instagram_<username>_post/reel/story_*.jpeg/mp4` - Downloaded media

## Code Style

- Functional/procedural style preferred over OOP
- Global configuration variables set via exec() of CONFIG_BLOCK
- Signal handlers for runtime control (USR1, USR2, TRAP, ABRT, HUP)
- Python 3.9+ required
