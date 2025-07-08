import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class GroupsDatabase:
    def __init__(self, db_file='groups.json'):
        self.db_file = db_file
        self.groups = self.load_groups()

    def load_groups(self):
        """Load groups from JSON file"""
        try:
            if os.path.exists(self.db_file):
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading groups database: {e}")
            return {}

    def save_groups(self):
        """Save groups to JSON file"""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.groups, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving groups database: {e}")

    def add_group(self, group_id, group_title, group_type, username=None, invite_link=None):
        """Add or update a group in the database"""
        try:
            group_id_str = str(group_id)
            current_time = datetime.now().isoformat()
            
            if group_id_str not in self.groups:
                # New group
                self.groups[group_id_str] = {
                    'id': group_id,
                    'title': group_title,
                    'type': group_type,  # 'group', 'supergroup', 'channel'
                    'username': username,
                    'invite_link': invite_link,
                    'added_date': current_time,
                    'last_interaction': current_time,
                    'interaction_count': 1,
                    'is_active': True
                }
                logger.info(f"Added new group: {group_title} ({group_id})")
            else:
                # Update existing group
                self.groups[group_id_str].update({
                    'title': group_title,
                    'type': group_type,
                    'username': username,
                    'invite_link': invite_link,
                    'last_interaction': current_time,
                    'is_active': True
                })
                logger.info(f"Updated group: {group_title} ({group_id})")
            
            self.save_groups()
        except Exception as e:
            logger.error(f"Error adding group to database: {e}")

    def increment_interaction(self, group_id):
        """Increment interaction count for a group"""
        try:
            group_id_str = str(group_id)
            if group_id_str in self.groups:
                self.groups[group_id_str]['interaction_count'] += 1
                self.groups[group_id_str]['last_interaction'] = datetime.now().isoformat()
                self.save_groups()
        except Exception as e:
            logger.error(f"Error incrementing interaction for group {group_id}: {e}")

    def mark_group_inactive(self, group_id):
        """Mark a group as inactive (bot was removed)"""
        try:
            group_id_str = str(group_id)
            if group_id_str in self.groups:
                self.groups[group_id_str]['is_active'] = False
                self.groups[group_id_str]['last_interaction'] = datetime.now().isoformat()
                self.save_groups()
        except Exception as e:
            logger.error(f"Error marking group {group_id} as inactive: {e}")

    def get_total_groups(self):
        """Get total number of groups"""
        return len([g for g in self.groups.values() if g.get('is_active', True)])

    def get_all_groups(self):
        """Get all active groups"""
        return {k: v for k, v in self.groups.items() if v.get('is_active', True)}

    def get_recent_groups(self, limit=10):
        """Get recently added groups"""
        active_groups = [(k, v) for k, v in self.groups.items() if v.get('is_active', True)]
        # Sort by added_date (most recent first)
        sorted_groups = sorted(active_groups, key=lambda x: x[1].get('added_date', ''), reverse=True)
        return sorted_groups[:limit]

    def get_group_stats(self):
        """Get comprehensive group statistics"""
        active_groups = self.get_all_groups()
        total_groups = len(active_groups)
        total_interactions = sum(g.get('interaction_count', 0) for g in active_groups.values())
        
        # Group by type
        type_counts = {}
        for group in active_groups.values():
            group_type = group.get('type', 'unknown')
            type_counts[group_type] = type_counts.get(group_type, 0) + 1
        
        # Public vs Private groups
        public_groups = len([g for g in active_groups.values() if g.get('username')])
        private_groups = total_groups - public_groups
        
        return {
            'total_groups': total_groups,
            'total_interactions': total_interactions,
            'type_counts': type_counts,
            'public_groups': public_groups,
            'private_groups': private_groups
        }

    def get_group_by_id(self, group_id):
        """Get group information by ID"""
        group_id_str = str(group_id)
        return self.groups.get(group_id_str)

# Initialize global groups database
groups_db = GroupsDatabase()
