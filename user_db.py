import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class UserDatabase:
    def __init__(self, db_file: str = "users.json"):
        self.db_file = db_file
        self.users = self._load_users()
    
    def _load_users(self) -> Dict:
        """Load users from JSON file"""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading users database: {e}")
            return {}
    
    def _save_users(self):
        """Save users to JSON file"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving users database: {e}")
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None, last_name: str = None):
        """Add or update user in database"""
        user_id_str = str(user_id)
        current_time = datetime.now().isoformat()
        
        if user_id_str not in self.users:
            # New user
            self.users[user_id_str] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'joined_date': current_time,
                'last_seen': current_time,
                'interaction_count': 1
            }
            logger.info(f"New user added: {user_id} ({first_name})")
        else:
            # Update existing user
            self.users[user_id_str].update({
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'last_seen': current_time,
                'interaction_count': self.users[user_id_str].get('interaction_count', 0) + 1
            })
        
        self._save_users()
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        return self.users.get(str(user_id))
    
    def get_total_users(self) -> int:
        """Get total number of users"""
        return len(self.users)
    
    def get_recent_users(self, limit: int = 10) -> List[Dict]:
        """Get most recently joined users"""
        try:
            users_list = list(self.users.values())
            # Sort by joined_date in descending order
            users_list.sort(key=lambda x: x.get('joined_date', ''), reverse=True)
            return users_list[:limit]
        except Exception as e:
            logger.error(f"Error getting recent users: {e}")
            return []
    
    def get_all_user_ids(self) -> List[int]:
        """Get all user IDs for broadcasting"""
        return [int(user_id) for user_id in self.users.keys()]

    def get_all_users(self) -> dict:
        """Get all users data for export"""
        return self.users.copy()

# Global instance
user_db = UserDatabase()
