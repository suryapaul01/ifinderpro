"""
Group Database Management for ID Finder Pro Bot
Handles warnings, mutes, and other moderation data per group.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class GroupDatabase:
    """Database for group moderation data"""
    
    def __init__(self, db_file: str = "group_data.json"):
        self.db_file = db_file
        self.data = self._load_data()
    
    def _load_data(self) -> Dict:
        """Load data from JSON file"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading group database: {e}")
                return {}
        return {}
    
    def _save_data(self):
        """Save data to JSON file"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving group database: {e}")
    
    def _get_group_data(self, group_id: int) -> Dict:
        """Get or create group data structure"""
        group_key = str(group_id)
        if group_key not in self.data:
            self.data[group_key] = {
                'warnings': {},  # user_id: [{'reason': str, 'date': str, 'admin_id': int}]
                'mutes': {},     # user_id: {'until': str, 'reason': str, 'admin_id': int}
                'settings': {
                    'max_warnings': 3,
                    'auto_action': 'mute'  # 'mute', 'kick', 'ban'
                }
            }
        return self.data[group_key]
    
    # Warning System
    
    def add_warning(self, group_id: int, user_id: int, reason: str, admin_id: int) -> int:
        """Add a warning to a user. Returns total warning count."""
        group_data = self._get_group_data(group_id)
        user_key = str(user_id)
        
        if user_key not in group_data['warnings']:
            group_data['warnings'][user_key] = []
        
        warning = {
            'reason': reason,
            'date': datetime.now().isoformat(),
            'admin_id': admin_id
        }
        
        group_data['warnings'][user_key].append(warning)
        self._save_data()
        
        return len(group_data['warnings'][user_key])
    
    def get_warnings(self, group_id: int, user_id: int) -> List[Dict]:
        """Get all warnings for a user in a group"""
        group_data = self._get_group_data(group_id)
        user_key = str(user_id)
        return group_data['warnings'].get(user_key, [])
    
    def get_warning_count(self, group_id: int, user_id: int) -> int:
        """Get warning count for a user"""
        return len(self.get_warnings(group_id, user_id))
    
    def reset_warnings(self, group_id: int, user_id: int):
        """Reset all warnings for a user"""
        group_data = self._get_group_data(group_id)
        user_key = str(user_id)
        
        if user_key in group_data['warnings']:
            del group_data['warnings'][user_key]
            self._save_data()
    
    # Mute System
    
    def add_mute(self, group_id: int, user_id: int, duration: timedelta, reason: str, admin_id: int):
        """Add a mute for a user"""
        group_data = self._get_group_data(group_id)
        user_key = str(user_id)
        
        until_time = datetime.now() + duration
        
        group_data['mutes'][user_key] = {
            'until': until_time.isoformat(),
            'reason': reason,
            'admin_id': admin_id,
            'muted_at': datetime.now().isoformat()
        }
        
        self._save_data()
    
    def remove_mute(self, group_id: int, user_id: int):
        """Remove mute for a user"""
        group_data = self._get_group_data(group_id)
        user_key = str(user_id)
        
        if user_key in group_data['mutes']:
            del group_data['mutes'][user_key]
            self._save_data()
    
    def is_user_muted(self, group_id: int, user_id: int) -> bool:
        """Check if user is currently muted"""
        group_data = self._get_group_data(group_id)
        user_key = str(user_id)
        
        if user_key not in group_data['mutes']:
            return False
        
        mute_data = group_data['mutes'][user_key]
        until_time = datetime.fromisoformat(mute_data['until'])
        
        if datetime.now() > until_time:
            # Mute expired, remove it
            del group_data['mutes'][user_key]
            self._save_data()
            return False
        
        return True
    
    def get_mute_info(self, group_id: int, user_id: int) -> Optional[Dict]:
        """Get mute information for a user"""
        group_data = self._get_group_data(group_id)
        user_key = str(user_id)
        
        if user_key not in group_data['mutes']:
            return None
        
        mute_data = group_data['mutes'][user_key]
        until_time = datetime.fromisoformat(mute_data['until'])
        
        if datetime.now() > until_time:
            # Mute expired, remove it
            del group_data['mutes'][user_key]
            self._save_data()
            return None
        
        return {
            'until': until_time,
            'reason': mute_data['reason'],
            'admin_id': mute_data['admin_id'],
            'muted_at': datetime.fromisoformat(mute_data['muted_at'])
        }
    
    # Group Settings
    
    def get_group_settings(self, group_id: int) -> Dict:
        """Get group settings"""
        group_data = self._get_group_data(group_id)
        return group_data['settings']
    
    def update_group_settings(self, group_id: int, settings: Dict):
        """Update group settings"""
        group_data = self._get_group_data(group_id)
        group_data['settings'].update(settings)
        self._save_data()
    
    # Statistics
    
    def get_group_stats(self, group_id: int) -> Dict:
        """Get group moderation statistics"""
        group_data = self._get_group_data(group_id)
        
        total_warnings = sum(len(warnings) for warnings in group_data['warnings'].values())
        users_with_warnings = len(group_data['warnings'])
        active_mutes = len([mute for mute in group_data['mutes'].values() 
                           if datetime.fromisoformat(mute['until']) > datetime.now()])
        
        return {
            'total_warnings': total_warnings,
            'users_with_warnings': users_with_warnings,
            'active_mutes': active_mutes,
            'total_users_moderated': len(set(list(group_data['warnings'].keys()) + list(group_data['mutes'].keys())))
        }
    
    def cleanup_expired_mutes(self):
        """Clean up expired mutes from all groups"""
        current_time = datetime.now()
        
        for group_id, group_data in self.data.items():
            expired_users = []
            
            for user_id, mute_data in group_data['mutes'].items():
                until_time = datetime.fromisoformat(mute_data['until'])
                if current_time > until_time:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del group_data['mutes'][user_id]
        
        if expired_users:
            self._save_data()
            logger.info(f"Cleaned up {len(expired_users)} expired mutes")
