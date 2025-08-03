#!/usr/bin/env python3
"""
Discord Server Backup Tool
A utility for backing up and restoring Discord server structures using Discord tokens.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from backup_utils import create_backup_directory, save_backup, load_backup
from discord_api import DiscordAPI

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Discord Server Backup Tool')
    
    # Token argument
    parser.add_argument('--token', type=str, help='Discord user token')
    
    # Create subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Backup command
    backup_parser = subparsers.add_parser('backup', help='Backup a Discord server')
    backup_parser.add_argument('--server-id', type=str, required=True, help='ID of the server to backup')
    backup_parser.add_argument('--output', type=str, help='Output directory for backup (default: ./backups)')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore a Discord server from backup')
    restore_parser.add_argument('--backup-file', type=str, required=True, help='Path to the backup file')
    restore_parser.add_argument('--server-id', type=str, required=True, help='ID of the server to restore to')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available backups')
    list_parser.add_argument('--directory', type=str, help='Directory containing backups (default: ./backups)')
    
    return parser.parse_args()

async def backup_server(api, server_id, output_dir):
    """Backup a Discord server."""
    try:
        logger.info(f"Starting backup of server ID: {server_id}")
        
        # Create backup directory if it doesn't exist
        backup_dir = create_backup_directory(output_dir)
        
        # Get server details
        server = await api.get_server(server_id)
        if not server:
            logger.error(f"Server with ID {server_id} not found or you don't have access.")
            return False
        
        logger.info(f"Backing up server: {server.get('name', 'Unknown')}")
        
        # Get server components
        channels = await api.get_channels(server_id)
        roles = await api.get_roles(server_id)
        emojis = await api.get_emojis(server_id)
        stickers = await api.get_stickers(server_id)
        
        # Build backup data
        backup_data = {
            'server': server,
            'channels': channels,
            'roles': roles,
            'emojis': emojis,
            'stickers': stickers
        }
        
        # Save backup
        backup_filename = f"{server.get('name', server_id)}-{server_id}.json"
        backup_path = save_backup(backup_data, backup_dir, backup_filename)
        
        logger.info(f"Backup completed successfully and saved to: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error during backup: {str(e)}")
        return False

async def restore_server(api, backup_file, target_server_id):
    """Restore a Discord server from backup."""
    try:
        logger.info(f"Starting restoration to server ID: {target_server_id}")
        
        # Load backup data
        backup_data = load_backup(backup_file)
        if not backup_data:
            logger.error(f"Failed to load backup file: {backup_file}")
            return False
        
        # Get target server details to confirm it exists
        target_server = await api.get_server(target_server_id)
        if not target_server:
            logger.error(f"Target server with ID {target_server_id} not found or you don't have access.")
            return False
        
        logger.info(f"Restoring to server: {target_server.get('name', 'Unknown')}")
        
        # Delete existing channels, roles, emojis, stickers if they exist
        logger.info("Clearing existing server structure...")
        await api.clear_server(target_server_id)
        
        # Restore roles first (to preserve permissions)
        logger.info("Restoring roles...")
        role_id_map = await api.restore_roles(target_server_id, backup_data['roles'])
        
        # Restore channels
        logger.info("Restoring channels...")
        await api.restore_channels(target_server_id, backup_data['channels'], role_id_map)
        
        # Restore emojis
        logger.info("Restoring emojis...")
        await api.restore_emojis(target_server_id, backup_data['emojis'])
        
        # Restore stickers
        logger.info("Restoring stickers...")
        await api.restore_stickers(target_server_id, backup_data['stickers'])
        
        logger.info("Server restoration completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during restoration: {str(e)}")
        return False

def list_backups(directory):
    """List available backups."""
    backup_dir = Path(directory or './backups')
    
    if not backup_dir.exists():
        logger.info(f"Backup directory {backup_dir} does not exist.")
        return
    
    backup_files = list(backup_dir.glob('*.json'))
    
    if not backup_files:
        logger.info(f"No backup files found in {backup_dir}.")
        return
    
    logger.info(f"Found {len(backup_files)} backup files:")
    for file in backup_files:
        logger.info(f"- {file.name}")

async def main():
    """Main entry point for the application."""
    args = parse_arguments()
    
    # Get token from arguments or environment variable
    token = args.token or os.environ.get('DISCORD_TOKEN')
    if not token:
        logger.error("Discord token not provided. Use --token or set DISCORD_TOKEN environment variable.")
        sys.exit(1)
    
    # Initialize Discord API
    discord_api = DiscordAPI(token)
    
    if args.command == 'backup':
        output_dir = args.output or './backups'
        success = await backup_server(discord_api, args.server_id, output_dir)
        if not success:
            sys.exit(1)
    
    elif args.command == 'restore':
        success = await restore_server(discord_api, args.backup_file, args.server_id)
        if not success:
            sys.exit(1)
    
    elif args.command == 'list':
        list_backups(args.directory)
    
    else:
        logger.error("No command specified. Use 'backup', 'restore', or 'list'.")
        sys.exit(1)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
