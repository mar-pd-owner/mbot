"""
Advanced Database Management System for MBOT
Handles all data storage with encryption and optimization
"""

import json
import sqlite3
import threading
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import hashlib
from encryption import encryption
import pickle
import zlib

class DatabaseManager:
    def __init__(self):
        self.db_path = 'mbot_database.db'
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.connection_pool = {}
        self.initialized = False
        
        # Initialize database
        self.init_database()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self.periodic_cleanup)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
    
    def get_connection(self):
        """Get database connection from pool"""
        thread_id = threading.get_ident()
        
        if thread_id not in self.connection_pool:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connection_pool[thread_id] = conn
        
        return self.connection_pool[thread_id]
    
    def init_database(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_boosts INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                profile_views INTEGER DEFAULT 0,
                is_premium BOOLEAN DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'active',
                settings TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}',
                encrypted_data BLOB
            )
        ''')
        
        # User sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER,
                device_info TEXT,
                ip_address TEXT,
                user_agent TEXT,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Boosts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS boosts (
                boost_id TEXT PRIMARY KEY,
                user_id INTEGER,
                video_id TEXT,
                video_url TEXT,
                boost_type TEXT,
                target_count INTEGER,
                completed_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                duration REAL,
                average_rps REAL DEFAULT 0,
                peak_rps REAL DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Boost requests table (individual requests)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS boost_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                boost_id TEXT,
                device_id TEXT,
                proxy TEXT,
                success BOOLEAN,
                response_time REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (boost_id) REFERENCES boosts (boost_id)
            )
        ''')
        
        # Devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                device_id TEXT PRIMARY KEY,
                device_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Proxies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS proxies (
                proxy_id INTEGER PRIMARY KEY AUTOINCREMENT,
                proxy_string TEXT UNIQUE,
                proxy_type TEXT,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success_count INTEGER DEFAULT 0,
                failure_count INTEGER DEFAULT 0,
                response_time_avg REAL DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                country TEXT,
                anonymity_level TEXT
            )
        ''')
        
        # Analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_name TEXT,
                metric_value REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}'
            )
        ''')
        
        # Security logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                log_type TEXT,
                severity TEXT,
                ip_address TEXT,
                user_id INTEGER,
                description TEXT,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Messages table (for user-bot communication)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_type TEXT,
                content TEXT,
                direction TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_read BOOLEAN DEFAULT 0,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_boosts_user_id ON boosts(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_boosts_status ON boosts(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_boosts_timestamp ON boosts(start_time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_boost_requests_boost_id ON boost_requests(boost_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_timestamp ON analytics(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_logs_ip ON security_logs(ip_address)')
        
        conn.commit()
        self.initialized = True
        
        print("Database initialized successfully")
    
    # User Management Methods
    
    def add_user(self, telegram_id: int, username: str, first_name: str, 
                 last_name: str = "", phone: str = None) -> int:
        """Add new user to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO users 
                (telegram_id, username, first_name, last_name, phone, join_date, last_active)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            ''', (telegram_id, username, first_name, last_name, phone))
            
            conn.commit()
            
            # Get user ID
            cursor.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
            result = cursor.fetchone()
            
            return result['id'] if result else None
            
        except Exception as e:
            print(f"Error adding user: {e}")
            conn.rollback()
            return None
    
    def get_user(self, identifier: Union[int, str], by_telegram_id: bool = True) -> Optional[Dict]:
        """Get user by ID or telegram ID"""
        cache_key = f"user_{identifier}"
        
        with self.cache_lock:
            if cache_key in self.cache:
                cached_data = self.cache[cache_key]
                if time.time() - cached_data['timestamp'] < 60:  # 1 minute cache
                    return cached_data['data']
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if by_telegram_id:
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (identifier,))
        else:
            cursor.execute('SELECT * FROM users WHERE id = ?', (identifier,))
        
        row = cursor.fetchone()
        
        if row:
            user_data = dict(row)
            
            # Parse JSON fields
            for field in ['settings', 'metadata']:
                if user_data[field]:
                    try:
                        user_data[field] = json.loads(user_data[field])
                    except:
                        user_data[field] = {}
            
            # Cache the result
            with self.cache_lock:
                self.cache[cache_key] = {
                    'data': user_data,
                    'timestamp': time.time()
                }
            
            return user_data
        
        return None
    
    def update_user(self, user_id: int, updates: Dict):
        """Update user information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Build update query
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key in ['settings', 'metadata'] and isinstance(value, dict):
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            values.append(value)
        
        values.append(user_id)
        
        query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?"
        
        try:
            cursor.execute(query, values)
            conn.commit()
            
            # Clear cache
            cache_key = f"user_{user_id}"
            with self.cache_lock:
                if cache_key in self.cache:
                    del self.cache[cache_key]
            
        except Exception as e:
            print(f"Error updating user: {e}")
            conn.rollback()
    
    def update_user_activity(self, user_id: int):
        """Update user's last activity timestamp"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET last_active = datetime('now') 
            WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
    
    def increment_user_stat(self, user_id: int, stat_field: str, amount: int = 1):
        """Increment user statistic"""
        if stat_field not in ['total_boosts', 'total_likes', 'profile_views']:
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f'''
            UPDATE users 
            SET {stat_field} = {stat_field} + ? 
            WHERE id = ?
        ''', (amount, user_id))
        
        conn.commit()
    
    # Boost Management Methods
    
    def create_boost(self, user_id: int, video_id: str, video_url: str, 
                    boost_type: str, target_count: int) -> str:
        """Create new boost record"""
        boost_id = f"boost_{int(time.time())}_{hashlib.md5(video_id.encode()).hexdigest()[:8]}"
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO boosts 
            (boost_id, user_id, video_id, video_url, boost_type, target_count, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (boost_id, user_id, video_id, video_url, boost_type, target_count))
        
        conn.commit()
        
        return boost_id
    
    def update_boost(self, boost_id: str, updates: Dict):
        """Update boost information"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        set_clauses = []
        values = []
        
        for key, value in updates.items():
            if key == 'metadata' and isinstance(value, dict):
                value = json.dumps(value)
            set_clauses.append(f"{key} = ?")
            values.append(value)
        
        values.append(boost_id)
        
        query = f"UPDATE boosts SET {', '.join(set_clauses)} WHERE boost_id = ?"
        
        try:
            cursor.execute(query, values)
            conn.commit()
        except Exception as e:
            print(f"Error updating boost: {e}")
            conn.rollback()
    
    def log_boost_request(self, boost_id: str, device_id: str, proxy: str, 
                         success: bool, response_time: float, error_message: str = None):
        """Log individual boost request"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO boost_requests 
            (boost_id, device_id, proxy, success, response_time, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (boost_id, device_id, proxy, success, response_time, error_message))
        
        # Update boost counts
        if success:
            cursor.execute('''
                UPDATE boosts 
                SET completed_count = completed_count + 1 
                WHERE boost_id = ?
            ''', (boost_id,))
        else:
            cursor.execute('''
                UPDATE boosts 
                SET failed_count = failed_count + 1 
                WHERE boost_id = ?
            ''', (boost_id,))
        
        conn.commit()
    
    def get_boost_stats(self, boost_id: str) -> Dict:
        """Get boost statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM boosts WHERE boost_id = ?', (boost_id,))
        boost_row = cursor.fetchone()
        
        if not boost_row:
            return None
        
        boost_data = dict(boost_row)
        
        # Get request statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_requests,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                AVG(response_time) as avg_response_time,
                MIN(timestamp) as first_request,
                MAX(timestamp) as last_request
            FROM boost_requests 
            WHERE boost_id = ?
        ''', (boost_id,))
        
        stats_row = cursor.fetchone()
        boost_data['request_stats'] = dict(stats_row) if stats_row else {}
        
        return boost_data
    
    # Device Management Methods
    
    def add_device(self, device_info: str) -> str:
        """Add new device"""
        device_id = hashlib.md5(device_info.encode()).hexdigest()
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO devices 
            (device_id, device_info, created_at, last_used)
            VALUES (?, ?, datetime('now'), datetime('now'))
        ''', (device_id, device_info))
        
        conn.commit()
        
        return device_id
    
    def update_device_usage(self, device_id: str, success: bool):
        """Update device usage statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if success:
            cursor.execute('''
                UPDATE devices 
                SET usage_count = usage_count + 1,
                    success_count = success_count + 1,
                    last_used = datetime('now')
                WHERE device_id = ?
            ''', (device_id,))
        else:
            cursor.execute('''
                UPDATE devices 
                SET usage_count = usage_count + 1,
                    failure_count = failure_count + 1,
                    last_used = datetime('now')
                WHERE device_id = ?
            ''', (device_id,))
        
        conn.commit()
    
    def get_active_devices(self, limit: int = 100) -> List[Dict]:
        """Get active devices"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM devices 
            WHERE is_active = 1 
            ORDER BY success_count DESC, last_used DESC 
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    # Analytics Methods
    
    def log_metric(self, metric_name: str, metric_value: float, metadata: Dict = None):
        """Log analytics metric"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute('''
            INSERT INTO analytics (metric_name, metric_value, metadata)
            VALUES (?, ?, ?)
        ''', (metric_name, metric_value, metadata_json))
        
        conn.commit()
    
    def get_metrics(self, metric_name: str, hours: int = 24) -> List[Dict]:
        """Get metrics for specific time period"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM analytics 
            WHERE metric_name = ? 
            AND timestamp >= datetime('now', ?)
            ORDER BY timestamp ASC
        ''', (metric_name, f'-{hours} hours'))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_daily_summary(self, date: str = None) -> Dict:
        """Get daily summary statistics"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # User statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN date(last_active) = date(?) THEN 1 ELSE 0 END) as active_today,
                SUM(CASE WHEN status = 'banned' THEN 1 ELSE 0 END) as banned_users
            FROM users
        ''', (date,))
        user_stats = dict(cursor.fetchone())
        
        # Boost statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_boosts,
                SUM(target_count) as total_targeted,
                SUM(completed_count) as total_completed,
                AVG(duration) as avg_duration,
                AVG(average_rps) as avg_rps
            FROM boosts 
            WHERE date(start_time) = date(?)
        ''', (date,))
        boost_stats = dict(cursor.fetchone())
        
        # Device statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_devices,
                SUM(usage_count) as total_usage,
                SUM(success_count) as total_success,
                AVG(1.0 * success_count / usage_count) as success_rate
            FROM devices 
            WHERE is_active = 1
        ''')
        device_stats = dict(cursor.fetchone())
        
        return {
            'date': date,
            'user_stats': user_stats,
            'boost_stats': boost_stats,
            'device_stats': device_stats
        }
    
    # Security Methods
    
    def log_security_event(self, log_type: str, severity: str, ip_address: str, 
                          user_id: int = None, description: str = "", details: Dict = None):
        """Log security event"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        details_json = json.dumps(details or {})
        
        cursor.execute('''
            INSERT INTO security_logs 
            (log_type, severity, ip_address, user_id, description, details)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (log_type, severity, ip_address, user_id, description, details_json))
        
        conn.commit()
    
    def get_security_events(self, hours: int = 24, severity: str = None) -> List[Dict]:
        """Get security events"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM security_logs 
            WHERE timestamp >= datetime('now', ?)
        '''
        params = [f'-{hours} hours']
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        query += ' ORDER BY timestamp DESC'
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # Message Management Methods
    
    def add_message(self, user_id: int, message_type: str, content: str, 
                   direction: str, metadata: Dict = None) -> int:
        """Add message to database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata or {})
        
        cursor.execute('''
            INSERT INTO messages 
            (user_id, message_type, content, direction, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, message_type, content, direction, metadata_json))
        
        conn.commit()
        
        return cursor.lastrowid
    
    def get_user_messages(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user messages"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM messages 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            message = dict(row)
            if message['metadata']:
                try:
                    message['metadata'] = json.loads(message['metadata'])
                except:
                    message['metadata'] = {}
            messages.append(message)
        
        return messages
    
    def mark_message_read(self, message_id: int):
        """Mark message as read"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE messages 
            SET is_read = 1 
            WHERE message_id = ?
        ''', (message_id,))
        
        conn.commit()
    
    # Advanced Query Methods
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute custom query"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute(query, params)
        
        if query.strip().upper().startswith('SELECT'):
            return [dict(row) for row in cursor.fetchall()]
        else:
            conn.commit()
            return []
    
    def get_user_leaderboard(self, limit: int = 20, time_period: str = 'all') -> List[Dict]:
        """Get user leaderboard"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        time_filter = ''
        if time_period == 'today':
            time_filter = "AND date(b.start_time) = date('now')"
        elif time_period == 'week':
            time_filter = "AND b.start_time >= datetime('now', '-7 days')"
        elif time_period == 'month':
            time_filter = "AND b.start_time >= datetime('now', '-30 days')"
        
        cursor.execute(f'''
            SELECT 
                u.id,
                u.telegram_id,
                u.username,
                u.first_name,
                u.last_name,
                u.total_boosts,
                u.total_likes,
                COUNT(DISTINCT b.boost_id) as boost_count,
                SUM(b.completed_count) as total_completed,
                AVG(b.average_rps) as avg_rps
            FROM users u
            LEFT JOIN boosts b ON u.id = b.user_id {time_filter}
            WHERE u.status = 'active'
            GROUP BY u.id
            ORDER BY u.total_boosts DESC, total_completed DESC
            LIMIT ?
        ''', (limit,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_system_health(self) -> Dict:
        """Get system health status"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check database health
        cursor.execute("SELECT COUNT(*) as user_count FROM users")
        user_count = cursor.fetchone()['user_count']
        
        cursor.execute("SELECT COUNT(*) as boost_count FROM boosts WHERE status = 'completed'")
        boost_count = cursor.fetchone()['boost_count']
        
        cursor.execute("SELECT COUNT(*) as device_count FROM devices WHERE is_active = 1")
        device_count = cursor.fetchone()['device_count']
        
        # Check for recent errors
        cursor.execute('''
            SELECT COUNT(*) as error_count 
            FROM security_logs 
            WHERE severity IN ('high', 'critical') 
            AND timestamp >= datetime('now', '-1 hour')
        ''')
        error_count = cursor.fetchone()['error_count']
        
        # Calculate success rate
        cursor.execute('''
            SELECT 
                SUM(success_count) as total_success,
                SUM(usage_count) as total_usage
            FROM devices
            WHERE is_active = 1
        ''')
        device_stats = cursor.fetchone()
        
        success_rate = 0
        if device_stats['total_usage'] > 0:
            success_rate = device_stats['total_success'] / device_stats['total_usage'] * 100
        
        return {
            'database_status': 'healthy' if user_count > 0 else 'empty',
            'user_count': user_count,
            'boost_count': boost_count,
            'device_count': device_count,
            'recent_errors': error_count,
            'success_rate': round(success_rate, 2),
            'timestamp': datetime.now().isoformat()
        }
    
    # Maintenance Methods
    
    def periodic_cleanup(self):
        """Periodic cleanup of old data"""
        while True:
            time.sleep(3600)  # Run every hour
            
            try:
                self.cleanup_old_data()
                self.optimize_database()
                print("Database cleanup completed")
            except Exception as e:
                print(f"Error during database cleanup: {e}")
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Cleanup old data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Delete old boost requests
        cursor.execute('''
            DELETE FROM boost_requests 
            WHERE timestamp < datetime('now', ?)
        ''', (f'-{days_to_keep} days',))
        
        # Delete old analytics
        cursor.execute('''
            DELETE FROM analytics 
            WHERE timestamp < datetime('now', ?)
        ''', (f'-{days_to_keep} days',))
        
        # Delete old security logs (keep high severity)
        cursor.execute('''
            DELETE FROM security_logs 
            WHERE timestamp < datetime('now', ?)
            AND severity NOT IN ('high', 'critical')
        ''', (f'-{days_to_keep} days',))
        
        # Delete old messages
        cursor.execute('''
            DELETE FROM messages 
            WHERE timestamp < datetime('now', ?)
            AND is_read = 1
        ''', (f'-{days_to_keep} days',))
        
        # Deactivate old devices
        cursor.execute('''
            UPDATE devices 
            SET is_active = 0 
            WHERE last_used < datetime('now', ?)
            AND is_active = 1
        ''', (f'-{days_to_keep * 2} days',))
        
        conn.commit()
    
    def optimize_database(self):
        """Optimize database performance"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Vacuum database
        cursor.execute('VACUUM')
        
        # Update statistics
        cursor.execute('ANALYZE')
        
        conn.commit()
    
    def backup_database(self, backup_path: str = None):
        """Backup database"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f'backups/mbot_backup_{timestamp}.db'
        
        import shutil
        shutil.copy2(self.db_path, backup_path)
        
        # Compress backup
        with open(self.db_path, 'rb') as f_in:
            with open(f'{backup_path}.gz', 'wb') as f_out:
                import gzip
                with gzip.GzipFile(fileobj=f_out, mode='wb') as gz_out:
                    shutil.copyfileobj(f_in, gz_out)
        
        return backup_path
    
    def restore_database(self, backup_path: str):
        """Restore database from backup"""
        import shutil
        import os
        
        if os.path.exists(backup_path):
            # Close all connections
            for conn in self.connection_pool.values():
                conn.close()
            self.connection_pool.clear()
            
            # Restore backup
            shutil.copy2(backup_path, self.db_path)
            
            # Reinitialize
            self.initialized = False
            self.init_database()
            
            return True
        
        return False

# Global instance
db = DatabaseManager()
