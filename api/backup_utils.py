"""
Utility functions for Discord server backup and restoration.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

def create_backup_directory(base_dir: str = './backups') -> Path:
    """
    Create a backup directory if it doesn't exist.
    
    Args:
        base_dir: Base directory for backups
        
    Returns:
        Path object pointing to the backup directory
    """
    backup_dir = Path(base_dir)
    
    # Create directory if it doesn't exist
    if not backup_dir.exists():
        backup_dir.mkdir(parents=True)
        logger.info(f"Created backup directory: {backup_dir}")
    
    return backup_dir

def save_backup(backup_data: Dict, backup_dir: Path, filename: str) -> str:
    """
    Save backup data to a JSON file.
    
    Args:
        backup_data: The server data to backup
        backup_dir: Directory to save the backup
        filename: Name of the backup file
        
    Returns:
        Path to the saved backup file
    """
    # Add timestamp to filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename_with_timestamp = f"{timestamp}-{filename}"
    
    backup_path = backup_dir / filename_with_timestamp
    
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Backup saved to: {backup_path}")
        return str(backup_path)
    
    except Exception as e:
        logger.error(f"Error saving backup: {str(e)}")
        return None

def load_backup(backup_path: str) -> Optional[Dict]:
    """
    Load backup data from a JSON file.
    
    Args:
        backup_path: Path to the backup file
        
    Returns:
        The loaded backup data or None if loading failed
    """
    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        logger.info(f"Loaded backup from: {backup_path}")
        return backup_data
    
    except FileNotFoundError:
        logger.error(f"Backup file not found: {backup_path}")
        return None
    
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in backup file: {backup_path}")
        return None
    
    except Exception as e:
        logger.error(f"Error loading backup: {str(e)}")
        return None
