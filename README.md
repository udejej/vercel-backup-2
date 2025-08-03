# Discord Server Backup Tool

A utility for backing up and restoring Discord server structures using Discord tokens and server IDs.

## Features

- Backup Discord server structure including:
  - Channels and categories
  - Roles and permissions
  - Emojis and stickers
- Restore server structure from backup
- Command-line interface for easy usage
- JSON format for backups

## Requirements

- Python 3.9+
- Required packages:
  - discord.py
  - aiohttp
  - argparse

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/discord-server-backup.git
   cd discord-server-backup
   ```

2. Install dependencies:
   ```
   pip install discord.py aiohttp
   ```

## Usage

### How to get your Discord token and server IDs

**WARNING**: Your Discord user token provides full access to your Discord account. Never share it with anyone or expose it in public repositories.

1. To get your Discord token:
   - Open Discord in your browser
   - Press F12 to open Developer Tools
   - Go to the "Network" tab
   - Perform any action in Discord (like sending a message)
   - Look for a request to "discord.com"
   - Find the "Authorization" header in the request headers
   - This is your token

2. To get a server ID:
   - Enable Developer Mode in Discord (User Settings > Advanced > Developer Mode)
   - Right-click on the server icon and select "Copy ID"

### Backing up a server

