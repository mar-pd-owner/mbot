"""
User Management System for MBOT
Handles user data, profiles, and interactions
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import hashlib
from encryption import encryption

class UserManager:
    def __init__(self):
        self.users_file = 'users.json'
        self.banned_file = 'banned_users.json'
        self.stats_file = 'user_stats.json'
        self.users = self.load_users()
        self.banned_users = self.load_banned_users()
        self.user_stats = self.load_user_stats()
    
    def load_users(self) -> Dict:
        """Load users from encrypted file"""
        try:
            return encryption.secure_load(self.users_file)
        except:
            return {}
    
    def load_banned_users(self) -> List:
        """Load banned users"""
        try:
            with open(self.banned_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def load_user_stats(self) -> Dict:
        """Load user statistics"""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def save_users(self):
        """Save users to encrypted file"""
        encryption.secure_store(self.users, self.users_file)
    
    def save_banned_users(self):
        """Save banned users list"""
        with open(self.banned_file, 'w') as f:
            json.dump(self.banned_users, f)
    
    def save_user_stats(self):
        """Save user statistics"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.user_stats, f)
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str = ""):
        """Add new user"""
        if str(user_id) in self.users:
            return False
        
        user_data = {
            'id': user_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'join_date': datetime.now().isoformat(),
            'last_active': datetime.now().isoformat(),
            'total_boosts': 0,
            'total_likes': 0,
            'profile_views': 0,
            'is_premium': False,
            'is_verified': False,
            'status': 'active',
            'sessions': [],
            'devices': [],
            'subscription': None
        }
        
        self.users[str(user_id)] = user_data
        
        # Initialize stats
        self.user_stats[str(user_id)] = {
            'daily_boosts': 0,
            'weekly_boosts': 0,
            'monthly_boosts': 0,
            'total_requests': 0,
            'success_rate': 0.0,
            'last_boost_time': None
        }
        
        self.save_users()
        self.save_user_stats()
        
        return True
    
    def update_user_activity(self, user_id: int, activity_type: str, details: Dict = None):
        """Update user activity"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.users:
            return False
        
        # Update last active
        self.users[user_id_str]['last_active'] = datetime.now().isoformat()
        
        # Update based on activity type
        if activity_type == 'boost':
            self.users[user_id_str]['total_boosts'] += details.get('count', 1)
            self.update_stats(user_id, 'boost', details)
        elif activity_type == 'like':
            self.users[user_id_str]['total_likes'] += details.get('count', 1)
        elif activity_type == 'profile_view':
            self.users[user_id_str]['profile_views'] += 1
        elif activity_type == 'message':
            if 'messages' not in self.users[user_id_str]:
                self.users[user_id_str]['messages'] = []
            self.users[user_id_str]['messages'].append({
                'time': datetime.now().isoformat(),
                'type': details.get('type', 'text'),
                'length': details.get('length', 0)
            })
        
        self.save_users()
        return True
    
    def update_stats(self, user_id: int, stat_type: str, details: Dict):
        """Update user statistics"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.user_stats:
            self.user_stats[user_id_str] = {
                'daily_boosts': 0,
                'weekly_boosts': 0,
                'monthly_boosts': 0,
                'total_requests': 0,
                'success_rate': 0.0,
                'last_boost_time': None
            }
        
        stats = self.user_stats[user_id_str]
        today = datetime.now().date()
        
        if stat_type == 'boost':
            count = details.get('count', 1)
            success = details.get('success', True)
            
            # Reset daily stats if new day
            last_boost = stats.get('last_boost_time')
            if last_boost:
                last_date = datetime.fromisoformat(last_boost).date()
                if last_date != today:
                    stats['daily_boosts'] = 0
            
            stats['daily_boosts'] += count
            stats['weekly_boosts'] += count
            stats['monthly_boosts'] += count
            stats['total_requests'] += count
            
            # Update success rate
            total = stats['total_requests']
            if success:
                current_success = stats.get('successful_requests', 0) + 1
                stats['successful_requests'] = current_success
                stats['success_rate'] = (current_success / total) * 100
            
            stats['last_boost_time'] = datetime.now().isoformat()
        
        self.save_user_stats()
    
    def get_user_profile(self, user_id: int) -> Dict:
        """Get complete user profile"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.users:
            return None
        
        user_data = self.users[user_id_str].copy()
        
        # Add statistics
        if user_id_str in self.user_stats:
            user_data['stats'] = self.user_stats[user_id_str]
        
        # Calculate activity level
        user_data['activity_level'] = self.calculate_activity_level(user_id)
        
        # Add badges
        user_data['badges'] = self.get_user_badges(user_id)
        
        return user_data
    
    def calculate_activity_level(self, user_id: int) -> str:
        """Calculate user activity level"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.user_stats:
            return 'new'
        
        stats = self.user_stats[user_id_str]
        daily_boosts = stats.get('daily_boosts', 0)
        weekly_boosts = stats.get('weekly_boosts', 0)
        
        if daily_boosts > 100 or weekly_boosts > 500:
            return 'expert'
        elif daily_boosts > 50 or weekly_boosts > 200:
            return 'active'
        elif daily_boosts > 10 or weekly_boosts > 50:
            return 'regular'
        else:
            return 'casual'
    
    def get_user_badges(self, user_id: int) -> List[str]:
        """Get user achievement badges"""
        badges = []
        user_id_str = str(user_id)
        
        if user_id_str not in self.users:
            return badges
        
        user_data = self.users[user_id_str]
        stats = self.user_stats.get(user_id_str, {})
        
        # Check for badges
        if user_data['total_boosts'] >= 1000:
            badges.append('booster_expert')
        if user_data['total_boosts'] >= 100:
            badges.append('booster_pro')
        if user_data['total_boosts'] >= 10:
            badges.append('booster_beginner')
        
        if stats.get('success_rate', 0) > 95:
            badges.append('high_accuracy')
        
        if 'join_date' in user_data:
            join_date = datetime.fromisoformat(user_data['join_date'])
            days_since_join = (datetime.now() - join_date).days
            if days_since_join >= 30:
                badges.append('veteran')
            elif days_since_join >= 7:
                badges.append('regular')
        
        return badges
    
    def ban_user(self, user_id: int, reason: str = "Violation of terms"):
        """Ban a user"""
        user_id_str = str(user_id)
        
        if user_id_str in self.banned_users:
            return False
        
        self.banned_users.append(user_id_str)
        
        # Update user status
        if user_id_str in self.users:
            self.users[user_id_str]['status'] = 'banned'
            self.users[user_id_str]['ban_reason'] = reason
            self.users[user_id_str]['ban_date'] = datetime.now().isoformat()
        
        self.save_banned_users()
        self.save_users()
        
        return True
    
    def unban_user(self, user_id: int):
        """Unban a user"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.banned_users:
            return False
        
        self.banned_users.remove(user_id_str)
        
        # Update user status
        if user_id_str in self.users:
            self.users[user_id_str]['status'] = 'active'
            if 'ban_reason' in self.users[user_id_str]:
                del self.users[user_id_str]['ban_reason']
            if 'ban_date' in self.users[user_id_str]:
                del self.users[user_id_str]['ban_date']
        
        self.save_banned_users()
        self.save_users()
        
        return True
    
    def is_user_banned(self, user_id: int) -> bool:
        """Check if user is banned"""
        return str(user_id) in self.banned_users
    
    def get_all_users(self, limit: int = None) -> List[Dict]:
        """Get all users with optional limit"""
        users_list = list(self.users.values())
        
        # Sort by last active (most recent first)
        users_list.sort(key=lambda x: x.get('last_active', ''), reverse=True)
        
        if limit:
            users_list = users_list[:limit]
        
        return users_list
    
    def search_users(self, query: str) -> List[Dict]:
        """Search users by username or ID"""
        results = []
        query_lower = query.lower()
        
        for user_id, user_data in self.users.items():
            if (query_lower in str(user_id).lower() or
                query_lower in user_data.get('username', '').lower() or
                query_lower in user_data.get('first_name', '').lower() or
                (user_data.get('last_name') and query_lower in user_data['last_name'].lower())):
                
                results.append(user_data)
        
        return results
    
    def get_user_analytics(self, user_id: int) -> Dict:
        """Get detailed user analytics"""
        user_id_str = str(user_id)
        
        if user_id_str not in self.users:
            return None
        
        user_data = self.users[user_id_str]
        stats = self.user_stats.get(user_id_str, {})
        
        analytics = {
            'basic_info': {
                'id': user_data['id'],
                'username': user_data['username'],
                'name': f"{user_data['first_name']} {user_data['last_name']}",
                'join_date': user_data['join_date'],
                'status': user_data['status']
            },
            'activity': {
                'total_boosts': user_data['total_boosts'],
                'total_likes': user_data['total_likes'],
                'profile_views': user_data['profile_views'],
                'last_active': user_data['last_active'],
                'activity_level': self.calculate_activity_level(user_id)
            },
            'performance': {
                'success_rate': stats.get('success_rate', 0),
                'total_requests': stats.get('total_requests', 0),
                'daily_boosts': stats.get('daily_boosts', 0),
                'weekly_boosts': stats.get('weekly_boosts', 0),
                'monthly_boosts': stats.get('monthly_boosts', 0)
            },
            'badges': self.get_user_badges(user_id),
            'sessions': user_data.get('sessions', []),
            'devices': user_data.get('devices', [])
        }
        
        return analytics
    
    def cleanup_old_data(self, days: int = 30):
        """Clean up old user data"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        users_to_remove = []
        for user_id, user_data in self.users.items():
            last_active = datetime.fromisoformat(user_data.get('last_active', '2000-01-01'))
            if last_active < cutoff_date and user_data['total_boosts'] == 0:
                users_to_remove.append(user_id)
        
        for user_id in users_to_remove:
            del self.users[user_id]
            if user_id in self.user_stats:
                del self.user_stats[user_id]
        
        if users_to_remove:
            self.save_users()
            self.save_user_stats()
        
        return len(users_to_remove)

# Global instance
user_manager = UserManager()
