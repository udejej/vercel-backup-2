"""
Discord API Client
A module to interact with the Discord API for server backup and restoration operations.
"""

import aiohttp
import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Any, Tuple, Union, cast

logger = logging.getLogger(__name__)

class RateLimitHandler:
    """Handler for Discord API rate limits."""
    
    def __init__(self):
        self.reset_after = 0
        self.limit_remaining = None
        self.global_limit = False
        self.last_request_time = 0
    
    def update_from_headers(self, headers):
        """Update rate limit information from response headers."""
        if 'X-RateLimit-Remaining' in headers:
            self.limit_remaining = int(headers['X-RateLimit-Remaining'])
            
        if 'X-RateLimit-Reset-After' in headers:
            self.reset_after = float(headers['X-RateLimit-Reset-After'])
            
        if 'X-RateLimit-Global' in headers:
            self.global_limit = headers['X-RateLimit-Global'].lower() == 'true'
    
    async def handle_rate_limit(self):
        """Handle rate limiting by waiting if necessary."""
        # Always add a small delay between requests to avoid hitting rate limits
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Default delay between requests to prevent rate limits (600ms)
        min_delay = 0.6
        
        if time_since_last < min_delay:
            await asyncio.sleep(min_delay - time_since_last)
        
        # Handle explicit rate limits
        if self.limit_remaining is not None and self.limit_remaining <= 1:
            wait_time = self.reset_after + 1.0  # Add a larger buffer
            logger.warning(f"Rate limit hit, waiting for {wait_time} seconds")
            await asyncio.sleep(wait_time)
            self.limit_remaining = None
            self.reset_after = 0
            
        # Update the last request time
        self.last_request_time = time.time()

class DiscordAPI:
    """Discord API client for server backup and restoration."""
    
    API_BASE_URL = "https://discord.com/api/v10"
    
    def __init__(self, token):
        self.token = token
        self.rate_limit = RateLimitHandler()
        self.session = None
    
    async def _ensure_session(self):
        """Ensure that an HTTP session exists."""
        if self.session is None:
            self.session = aiohttp.ClientSession(headers={
                "Authorization": self.token,
                "Content-Type": "application/json",
                "User-Agent": "DiscordBackupTool/1.0"
            })
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _request(self, method, endpoint, **kwargs) -> Optional[Union[Dict, List]]:
        """Make a request to the Discord API with rate limit handling."""
        await self._ensure_session()
        url = f"{self.API_BASE_URL}{endpoint}"
        
        # Handle rate limits before making the request
        await self.rate_limit.handle_rate_limit()
        
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            # Vérifier que la session est toujours valide
            if self.session is None:
                await self._ensure_session()
                
            try:
                # Set a reasonable timeout for each request to prevent worker timeouts
                timeout = aiohttp.ClientTimeout(total=10)
                
                # Ensure we have a valid session (type checking fix)
                session = self.session
                if session is None:
                    await self._ensure_session()
                    session = cast(aiohttp.ClientSession, self.session)
                
                async with session.request(method, url, timeout=timeout, **kwargs) as response:
                    # Update rate limit information
                    self.rate_limit.update_from_headers(response.headers)
                    
                    # Handle different response statuses
                    if response.status == 429:  # Rate limited
                        retry_after = 1
                        try:
                            json_response = await response.json()
                            if 'retry_after' in json_response:
                                retry_after = json_response['retry_after']
                        except:
                            # If we can't decode JSON, use a default wait time
                            retry_after = 2
                        
                        # Add a bit of extra time to avoid hitting rate limits again
                        wait_time = retry_after + 1.0
                        logger.warning(f"Rate limited. Waiting for {wait_time} seconds.")
                        await asyncio.sleep(wait_time)
                        retry_count += 1
                        continue
                    
                    if response.status == 403:
                        logger.error(f"Permission denied for {endpoint}. Check your token and permissions.")
                        return None
                    
                    if response.status == 404:
                        logger.error(f"Resource not found: {endpoint}")
                        return None
                    
                    if 200 <= response.status < 300:
                        # Success - return JSON or empty dict if no content
                        if response.status != 204:  # 204 = No Content
                            try:
                                return await response.json()
                            except:
                                # Return empty dict if no valid JSON
                                return {}
                        return {}
                    
                    # Other error
                    try:
                        error_text = await response.text()
                        logger.error(f"API request failed with status {response.status}: {error_text}")
                    except:
                        logger.error(f"API request failed with status {response.status} (could not read response)")
                    
                    # Increase retry interval for server errors
                    if response.status >= 500:
                        await asyncio.sleep(2 * (retry_count + 1))
                    
                    retry_count += 1
                    continue
                    
            except aiohttp.ClientError as e:
                logger.error(f"HTTP error during API request: {str(e)}")
                retry_count += 1
                await asyncio.sleep(1.5 * (retry_count + 1))
            
            except asyncio.TimeoutError:
                logger.error("API request timed out")
                retry_count += 1
                await asyncio.sleep(1.5 * (retry_count + 1))
            
            except Exception as e:
                logger.error(f"Unexpected error during API request: {str(e)}")
                retry_count += 1
                await asyncio.sleep(2)
        
        logger.error(f"Failed after {max_retries} retries")
        return None
    
    async def get_server(self, server_id: str) -> Optional[Dict]:
        """Get information about a server."""
        return await self._request("GET", f"/guilds/{server_id}")
    
    async def get_channels(self, server_id: str) -> List[Dict]:
        """Get all channels in a server."""
        channels = await self._request("GET", f"/guilds/{server_id}/channels")
        if channels is None:
            return []
        if isinstance(channels, list):
            return channels
        return []
    
    async def get_roles(self, server_id: str) -> List[Dict]:
        """Get all roles in a server."""
        roles = await self._request("GET", f"/guilds/{server_id}/roles")
        if roles is None:
            return []
        if isinstance(roles, list):
            return roles
        return []
    
    async def get_emojis(self, server_id: str) -> List[Dict]:
        """Get all emojis in a server."""
        emojis = await self._request("GET", f"/guilds/{server_id}/emojis")
        if emojis is None:
            return []
        if isinstance(emojis, list):
            return emojis
        return []
    
    async def get_stickers(self, server_id: str) -> List[Dict]:
        """Get all stickers in a server."""
        stickers = await self._request("GET", f"/guilds/{server_id}/stickers")
        if stickers is None:
            return []
        if isinstance(stickers, list):
            return stickers
        return []
    
    async def clear_server(self, server_id: str) -> bool:
        """Clear existing channels and roles from a server."""
        try:
            # Get existing channels
            channels = await self.get_channels(server_id)
            
            # Delete channels (except system channels which cannot be deleted)
            for channel in channels:
                if not channel.get('type') == 4:  # Type 4 is category
                    await self._request("DELETE", f"/channels/{channel['id']}")
            
            # Delete categories after their child channels
            for channel in channels:
                if channel.get('type') == 4:  # Type 4 is category
                    await self._request("DELETE", f"/channels/{channel['id']}")
            
            # Get existing roles
            roles = await self.get_roles(server_id)
            
            # Delete roles (except @everyone which cannot be deleted)
            for role in roles:
                if role['name'] != '@everyone':
                    await self._request("DELETE", f"/guilds/{server_id}/roles/{role['id']}")
            
            return True
        except Exception as e:
            logger.error(f"Error clearing server: {str(e)}")
            return False
    
    async def restore_roles(self, server_id: str, roles: List[Dict]) -> Dict[str, str]:
        """Restore roles to a server and return a mapping of old role IDs to new role IDs."""
        role_id_map = {}
        
        # Sort roles by position to ensure proper hierarchy
        sorted_roles = sorted(roles, key=lambda r: r.get('position', 0))
        
        for role in sorted_roles:
            # Skip @everyone role as it already exists
            if role['name'] == '@everyone':
                # Still add it to the ID map
                everyone_role = [r for r in await self.get_roles(server_id) if r['name'] == '@everyone'][0]
                role_id_map[role['id']] = everyone_role['id']
                continue
            
            # Prepare role data for creation
            role_data = {
                'name': role['name'],
                'permissions': role['permissions'],
                'color': role.get('color', 0),
                'hoist': role.get('hoist', False),
                'mentionable': role.get('mentionable', False)
            }
            
            # Create the role
            new_role = await self._request("POST", f"/guilds/{server_id}/roles", json=role_data)
            
            if new_role:
                role_id_map[role['id']] = new_role['id']
                logger.info(f"Created role: {role['name']}")
            else:
                logger.warning(f"Failed to create role: {role['name']}")
        
        return role_id_map
    
    async def restore_channels(self, server_id: str, channels: List[Dict], role_id_map: Dict[str, str]):
        """Restore channels to a server."""
        # First create categories
        category_id_map = {}
        
        # Sort channels to ensure categories are created first
        categories = [c for c in channels if c.get('type') == 4]  # Type 4 is category
        
        for category in categories:
            # Prepare permission overwrites with mapped role IDs
            permission_overwrites = []
            for overwrite in category.get('permission_overwrites', []):
                if overwrite['type'] == 0 and overwrite['id'] in role_id_map:  # Type 0 is role
                    permission_overwrites.append({
                        'id': role_id_map[overwrite['id']],
                        'type': overwrite['type'],
                        'allow': overwrite.get('allow', '0'),
                        'deny': overwrite.get('deny', '0')
                    })
                elif overwrite['type'] == 1:  # Type 1 is member, keep as is
                    permission_overwrites.append(overwrite)
            
            # Create category
            category_data = {
                'name': category['name'],
                'type': 4,
                'permission_overwrites': permission_overwrites,
                'position': category.get('position', 0)
            }
            
            new_category = await self._request("POST", f"/guilds/{server_id}/channels", json=category_data)
            
            if new_category:
                category_id_map[category['id']] = new_category['id']
                logger.info(f"Created category: {category['name']}")
            else:
                logger.warning(f"Failed to create category: {category['name']}")
        
        # Then create text and voice channels
        non_categories = [c for c in channels if c.get('type') != 4]
        
        for channel in non_categories:
            # Prepare permission overwrites with mapped role IDs
            permission_overwrites = []
            for overwrite in channel.get('permission_overwrites', []):
                if overwrite['type'] == 0 and overwrite['id'] in role_id_map:  # Type 0 is role
                    permission_overwrites.append({
                        'id': role_id_map[overwrite['id']],
                        'type': overwrite['type'],
                        'allow': overwrite.get('allow', '0'),
                        'deny': overwrite.get('deny', '0')
                    })
                elif overwrite['type'] == 1:  # Type 1 is member, keep as is
                    permission_overwrites.append(overwrite)
            
            # Prepare channel data
            channel_data = {
                'name': channel['name'],
                'type': channel['type'],
                'permission_overwrites': permission_overwrites,
                'topic': channel.get('topic', ''),
                'nsfw': channel.get('nsfw', False),
                'rate_limit_per_user': channel.get('rate_limit_per_user', 0),
                'position': channel.get('position', 0)
            }
            
            # Add parent category if applicable
            if channel.get('parent_id') and channel['parent_id'] in category_id_map:
                channel_data['parent_id'] = category_id_map[channel['parent_id']]
            
            # Add voice-specific properties if this is a voice channel
            if channel['type'] == 2:  # Type 2 is voice channel
                channel_data['bitrate'] = channel.get('bitrate', 64000)
                channel_data['user_limit'] = channel.get('user_limit', 0)
            
            new_channel = await self._request("POST", f"/guilds/{server_id}/channels", json=channel_data)
            
            if new_channel:
                logger.info(f"Created channel: {channel['name']}")
            else:
                logger.warning(f"Failed to create channel: {channel['name']}")
    
    async def restore_emojis(self, server_id: str, emojis: List[Dict]):
        """Restore emojis to a server."""
        for emoji in emojis:
            # Emojis need to be re-uploaded as images
            if 'image' in emoji and emoji['available']:
                # Create emoji
                emoji_data = {
                    'name': emoji['name'],
                    'image': emoji['image'],
                    'roles': []  # We can't map roles for emojis easily
                }
                
                new_emoji = await self._request("POST", f"/guilds/{server_id}/emojis", json=emoji_data)
                
                if new_emoji:
                    logger.info(f"Created emoji: {emoji['name']}")
                else:
                    logger.warning(f"Failed to create emoji: {emoji['name']}")
    
    async def restore_stickers(self, server_id: str, stickers: List[Dict]):
        """Restore stickers to a server."""
        for sticker in stickers:
            # Stickers need to be re-uploaded as images
            if 'image' in sticker:
                # Create sticker
                sticker_data = {
                    'name': sticker['name'],
                    'description': sticker.get('description', ''),
                    'tags': sticker.get('tags', ''),
                    'file': sticker['image']
                }
                
                new_sticker = await self._request("POST", f"/guilds/{server_id}/stickers", json=sticker_data)
                
                if new_sticker:
                    logger.info(f"Created sticker: {sticker['name']}")
                else:
                    logger.warning(f"Failed to create sticker: {sticker['name']}")
