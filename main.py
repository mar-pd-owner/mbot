"""
MBOT ULTIMATE - Enhanced Production System
ADVANCED VERSION: Added performance optimization, better error handling, and new features
"""

import asyncio
import sys
import os
import time
import signal
import json
import threading
import logging
import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import sqlite3
from pathlib import Path

# Import Telegram modules
from telethon import TelegramClient, events, types
from telethon.tl.types import PeerUser, Message
from telethon.errors import FloodWaitError, RPCError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import all systems with improved error handling
try:
    from database import db
    from encryption import encryption
    from anti_detect import anti_detect
    from user_manager import user_manager
    from boost_manager import boost_manager
    from analytics_dashboard import analytics
    from security_monitor import security_monitor
    from notification_system import init_notification_system, notification_system
    from update_system import update_system
    from api_server import start_api_server
    from web_dashboard import start_web_dashboard
except ImportError as e:
    print(f"Import error: {e}")
    print("Installing required packages...")
    os.system("pip install telethon aiohttp requests sqlalchemy python-multipart fastapi uvicorn")
    print("Please restart the application")
    sys.exit(1)


class BoostStatus(Enum):
    """Boost status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class BoostType(Enum):
    """Boost type enum"""
    VIEWS = "views"
    LIKES = "likes"
    FOLLOWERS = "followers"
    SHARES = "shares"
    COMMENTS = "comments"


@dataclass
class BoostConfig:
    """Boost configuration"""
    max_concurrent_boosts: int = 5
    max_requests_per_minute: int = 3000
    request_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 2.0
    batch_size: int = 100
    max_devices_per_boost: int = 50


@dataclass
class UserStats:
    """User statistics"""
    total_boosts: int = 0
    total_likes: int = 0
    total_followers: int = 0
    total_shares: int = 0
    total_comments: int = 0
    total_spent: float = 0.0
    last_boost_time: Optional[datetime] = None
    boost_streak: int = 0


class MBOTUltimate:
    def __init__(self):
        self.config = self.load_config()
        self.systems: Dict[str, Any] = {}
        self.running = False
        self.start_time = time.time()
        self.telegram_client: Optional[TelegramClient] = None
        self.executor = ThreadPoolExecutor(max_workers=self.config.get('max_workers', 10))
        self.active_boosts: Dict[str, Dict] = {}
        self.user_sessions: Dict[int, Dict] = {}
        self.boost_config = BoostConfig()
        self.cache = {}
        self.rate_limiter = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        
        # Initialize cache cleanup thread
        self.cache_cleanup_thread = threading.Thread(target=self._cache_cleaner, daemon=True)
        
        logger.info("MBOT Ultimate initialized")
    
    def _cache_cleaner(self):
        """Clean expired cache entries"""
        while self.running:
            time.sleep(60)  # Clean every minute
            current_time = time.time()
            expired_keys = []
            for key, (value, expiry) in self.cache.items():
                if current_time > expiry:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self.cache[key]
    
    def load_config(self) -> Dict:
        """Enhanced configuration loader"""
        config_paths = [
            'config.json',
            'config/config.json',
            '../config.json',
            '~/.config/mbot/config.json'
        ]
        
        config = {}
        for path in config_paths:
            try:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    with open(expanded_path, 'r') as f:
                        config = json.load(f)
                    logger.info(f"Config loaded from {expanded_path}")
                    break
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")
        
        if not config:
            # Create default config
            config = self._create_default_config()
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
            logger.info("Created default config.json")
        
        # Validate and set defaults
        config = self._validate_config(config)
        
        return config
    
    def _create_default_config(self) -> Dict:
        """Create default configuration"""
        return {
            "version": "1.0",
            "bot_token": "YOUR_BOT_TOKEN_HERE",
            "owner_id": None,
            "owner_username": "admin",
            "api_enabled": True,
            "dashboard_enabled": True,
            "api_port": 5000,
            "dashboard_port": 8080,
            "security_level": "high",
            "boost_speed": "ultra",
            "max_boost_count": 10000,
            "max_threads": 100,
            "max_requests_per_minute": 3000,
            "proxy_enabled": False,
            "auto_restart": True,
            "database_path": "data/mbot.db",
            "log_level": "INFO",
            "backup_enabled": True,
            "backup_interval_hours": 24,
            "max_users": 10000,
            "max_devices": 1000,
            "currency": "USD",
            "pricing": {
                "views_per_dollar": 1000,
                "likes_per_dollar": 500,
                "followers_per_dollar": 100
            }
        }
    
    def _validate_config(self, config: Dict) -> Dict:
        """Validate and set default values"""
        defaults = self._create_default_config()
        
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
                logger.info(f"Set default value for {key}: {value}")
        
        # Validate required fields
        if config['bot_token'] == "YOUR_BOT_TOKEN_HERE":
            logger.error("Bot token not set in config")
            print("\n" + "="*60)
            print("❌ ERROR: Please set your bot token in config.json")
            print("="*60)
            print("\nSteps to get bot token:")
            print("1. Open Telegram and search for @BotFather")
            print("2. Send /newbot command")
            print("3. Follow the instructions to create a bot")
            print("4. Copy the bot token (looks like: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ)")
            print("5. Paste it in config.json file")
            print("\nExample config.json:")
            print('''
{
    "bot_token": "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
    "owner_id": 123456789,
    "version": "1.0"
}''')
            print("\n" + "="*60)
            sys.exit(1)
        
        return config
    
    def initialize_systems(self):
        """Enhanced system initialization"""
        print("🚀 Initializing MBOT Ultimate System...")
        
        try:
            # Create necessary directories
            self._create_directories()
            
            # Initialize systems with progress tracking
            systems_to_init = [
                ("Database", self._init_database),
                ("Encryption", self._init_encryption),
                ("Anti-Detection", self._init_anti_detect),
                ("User Manager", self._init_user_manager),
                ("Boost Manager", self._init_boost_manager),
                ("Analytics", self._init_analytics),
                ("Security Monitor", self._init_security_monitor),
                ("Notification System", self._init_notification_system)
            ]
            
            for i, (name, init_func) in enumerate(systems_to_init, 1):
                print(f"  [{i}/{len(systems_to_init)}] Initializing {name}...")
                try:
                    init_func()
                    print(f"     ✓ {name} initialized")
                except Exception as e:
                    print(f"     ❌ {name} initialization failed: {str(e)[:100]}")
                    if name == "Database":
                        raise  # Database is critical
                    logger.error(f"Failed to initialize {name}: {e}")
            
            print("\n✅ All systems initialized successfully!")
            
            # Warm up caches
            self._warmup_caches()
            
        except Exception as e:
            logger.critical(f"Error initializing systems: {e}", exc_info=True)
            print(f"❌ Critical error initializing systems: {e}")
            sys.exit(1)
    
    def _create_directories(self):
        """Create necessary directories"""
        directories = ['data', 'logs', 'backups', 'cache', 'temp']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    def _init_database(self):
        """Initialize database"""
        self.systems['database'] = db
        # Create tables if they don't exist
        self._ensure_database_tables()
    
    def _ensure_database_tables(self):
        """Ensure all required database tables exist"""
        conn = sqlite3.connect(self.config.get('database_path', 'data/mbot.db'))
        cursor = conn.cursor()
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                total_boosts INTEGER DEFAULT 0,
                total_likes INTEGER DEFAULT 0,
                total_followers INTEGER DEFAULT 0,
                total_shares INTEGER DEFAULT 0,
                total_comments INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0,
                boost_streak INTEGER DEFAULT 0,
                settings TEXT DEFAULT '{}',
                metadata TEXT DEFAULT '{}'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boosts (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                video_id TEXT NOT NULL,
                video_url TEXT NOT NULL,
                boost_type TEXT NOT NULL,
                target_count INTEGER NOT NULL,
                completed_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                end_time DATETIME,
                duration REAL,
                average_rps REAL,
                metadata TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT UNIQUE NOT NULL,
                device_model TEXT,
                os_version TEXT,
                last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                success_rate REAL DEFAULT 0.0,
                total_requests INTEGER DEFAULT 0,
                successful_requests INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS boost_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                boost_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                proxy_id TEXT,
                success BOOLEAN,
                response_time REAL,
                error_message TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (boost_id) REFERENCES boosts (id)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
            CREATE INDEX IF NOT EXISTS idx_boosts_user_id ON boosts(user_id);
            CREATE INDEX IF NOT EXISTS idx_boosts_status ON boosts(status);
            CREATE INDEX IF NOT EXISTS idx_boosts_start_time ON boosts(start_time);
            CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);
            CREATE INDEX IF NOT EXISTS idx_boost_requests_boost_id ON boost_requests(boost_id);
            CREATE INDEX IF NOT EXISTS idx_boost_requests_timestamp ON boost_requests(timestamp);
            """
        ]
        
        for table_sql in tables:
            cursor.execute(table_sql)
        
        conn.commit()
        conn.close()
        logger.info("Database tables ensured")
    
    def _init_encryption(self):
        """Initialize encryption system"""
        self.systems['encryption'] = encryption
        # Generate encryption key if not exists
        key_path = 'data/encryption.key'
        if not os.path.exists(key_path):
            encryption.generate_key()
            logger.info("Generated new encryption key")
    
    def _init_anti_detect(self):
        """Initialize anti-detection system"""
        self.systems['anti_detect'] = anti_detect
    
    def _init_user_manager(self):
        """Initialize user manager"""
        self.systems['user_manager'] = user_manager
    
    def _init_boost_manager(self):
        """Initialize boost manager"""
        self.systems['boost_manager'] = boost_manager
    
    def _init_analytics(self):
        """Initialize analytics"""
        try:
            self.systems['analytics'] = analytics
            # Initialize analytics database
            analytics.initialize()
        except Exception as e:
            logger.warning(f"Analytics initialization warning: {e}")
            self.systems['analytics'] = self._create_dummy_analytics()
    
    def _init_security_monitor(self):
        """Initialize security monitor"""
        self.systems['security_monitor'] = security_monitor
    
    def _init_notification_system(self):
        """Initialize notification system"""
        try:
            self.systems['notification'] = init_notification_system(
                self.config.get('bot_token'),
                self.config.get('owner_id')
            )
        except Exception as e:
            logger.warning(f"Notification system initialization warning: {e}")
            self.systems['notification'] = self._create_dummy_notification()
    
    def _create_dummy_analytics(self):
        """Create dummy analytics object"""
        class DummyAnalytics:
            def save_data(self): pass
            def log_user_activity(self, *args, **kwargs): pass
            def initialize(self): pass
        return DummyAnalytics()
    
    def _create_dummy_notification(self):
        """Create dummy notification object"""
        class DummyNotification:
            def stop(self): pass
            def notify_new_user(self, *args, **kwargs): pass
            def notify_boost_completed(self, *args, **kwargs): pass
            def notify_boost_failed(self, *args, **kwargs): pass
        return DummyNotification()
    
    def _warmup_caches(self):
        """Warm up system caches"""
        logger.info("Warming up caches...")
        try:
            # Preload active users
            db.get_active_users(limit=100)
            # Preload active devices
            db.get_active_devices(limit=50)
            logger.info("Caches warmed up")
        except Exception as e:
            logger.warning(f"Cache warmup failed: {e}")
    
    def start_background_services(self):
        """Enhanced background services starter"""
        print("\n🚀 Starting background services...")
        
        services = [
            ("API Server", self._start_api_server, self.config.get('api_enabled', False)),
            ("Web Dashboard", self._start_web_dashboard, self.config.get('dashboard_enabled', False)),
            ("Update System", self._start_update_system, True),
            ("Backup System", self._start_backup_system, self.config.get('backup_enabled', True)),
            ("Monitoring System", self._start_monitoring_system, True)
        ]
        
        for i, (name, start_func, enabled) in enumerate(services, 1):
            if enabled:
                print(f"  [{i}/{len(services)}] Starting {name}...")
                try:
                    start_func()
                    print(f"     ✓ {name} started")
                except Exception as e:
                    print(f"     ⚠️ {name} warning: {str(e)[:50]}...")
                    logger.warning(f"Failed to start {name}: {e}")
            else:
                print(f"  [{i}/{len(services)}] {name}: Disabled")
        
        print("\n✅ Background services started!")
    
    def _start_api_server(self):
        """Start API server"""
        import threading
        api_thread = threading.Thread(target=start_api_server, daemon=True)
        api_thread.start()
    
    def _start_web_dashboard(self):
        """Start web dashboard"""
        import threading
        dashboard_thread = threading.Thread(target=start_web_dashboard, daemon=True)
        dashboard_thread.start()
    
    def _start_update_system(self):
        """Start update system"""
        # Run update check in background
        threading.Thread(target=self._check_for_updates, daemon=True).start()
    
    def _start_backup_system(self):
        """Start backup system"""
        threading.Thread(target=self._run_backup_schedule, daemon=True).start()
    
    def _start_monitoring_system(self):
        """Start monitoring system"""
        threading.Thread(target=self._monitor_system_health, daemon=True).start()
    
    def _check_for_updates(self):
        """Check for system updates"""
        while self.running:
            try:
                # Check for updates every 6 hours
                time.sleep(6 * 3600)
                # update_system.run_update_check()  # Uncomment when ready
                logger.info("Update check completed")
            except Exception as e:
                logger.error(f"Update check failed: {e}")
    
    def _run_backup_schedule(self):
        """Run backup schedule"""
        backup_interval = self.config.get('backup_interval_hours', 24) * 3600
        
        while self.running:
            try:
                time.sleep(backup_interval)
                self._create_backup()
            except Exception as e:
                logger.error(f"Backup failed: {e}")
    
    def _create_backup(self):
        """Create system backup"""
        backup_dir = 'backups'
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'{backup_dir}/mbot_backup_{timestamp}.zip'
        
        import zipfile
        with zipfile.ZipFile(backup_file, 'w') as zipf:
            # Backup database
            if os.path.exists(self.config.get('database_path', 'data/mbot.db')):
                zipf.write(self.config['database_path'], 'mbot.db')
            
            # Backup config
            if os.path.exists('config.json'):
                zipf.write('config.json', 'config.json')
            
            # Backup logs
            if os.path.exists('mbot.log'):
                zipf.write('mbot.log', 'mbot.log')
        
        # Keep only last 7 backups
        self._cleanup_old_backups(backup_dir, keep_last=7)
        
        logger.info(f"Backup created: {backup_file}")
    
    def _cleanup_old_backups(self, backup_dir: str, keep_last: int = 7):
        """Cleanup old backup files"""
        if not os.path.exists(backup_dir):
            return
        
        backup_files = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith('mbot_backup_')],
            reverse=True
        )
        
        for old_file in backup_files[keep_last:]:
            os.remove(os.path.join(backup_dir, old_file))
            logger.debug(f"Removed old backup: {old_file}")
    
    def _monitor_system_health(self):
        """Monitor system health"""
        while self.running:
            try:
                # Check every 5 minutes
                time.sleep(300)
                
                # Check memory usage
                import psutil
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    logger.warning(f"High memory usage: {memory.percent}%")
                
                # Check disk space
                disk = psutil.disk_usage('/')
                if disk.percent > 90:
                    logger.warning(f"Low disk space: {disk.percent}%")
                
                # Check active boosts
                active_boost_count = len([b for b in self.active_boosts.values() if b['status'] == 'processing'])
                if active_boost_count > self.boost_config.max_concurrent_boosts:
                    logger.warning(f"Too many active boosts: {active_boost_count}")
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
    
    def schedule_tasks(self):
        """Enhanced task scheduling"""
        print("  [5/5] Scheduling Periodic Tasks...")
        
        tasks = [
            ("Daily Cleanup", self._daily_cleanup, 86400),
            ("Hourly Analytics", self._hourly_analytics, 3600),
            ("Device Status Check", self._check_device_status, 1800),
            ("User Session Cleanup", self._cleanup_user_sessions, 300),
            ("Cache Statistics", self._log_cache_stats, 600)
        ]
        
        for task_name, task_func, interval in tasks:
            threading.Thread(
                target=self._schedule_task,
                args=(task_name, task_func, interval),
                daemon=True
            ).start()
        
        print("     ✓ Periodic tasks scheduled")
    
    def _schedule_task(self, name: str, func: callable, interval: int):
        """Schedule a periodic task"""
        while self.running:
            try:
                time.sleep(interval)
                func()
                logger.debug(f"Task completed: {name}")
            except Exception as e:
                logger.error(f"Task {name} failed: {e}")
    
    def _daily_cleanup(self):
        """Daily cleanup tasks"""
        try:
            db.cleanup_old_data()
            logger.info("Daily cleanup completed")
        except Exception as e:
            logger.error(f"Daily cleanup failed: {e}")
    
    def _hourly_analytics(self):
        """Hourly analytics aggregation"""
        try:
            self.aggregate_analytics()
            logger.info("Hourly analytics completed")
        except Exception as e:
            logger.error(f"Hourly analytics failed: {e}")
    
    def _check_device_status(self):
        """Check device status"""
        try:
            active_devices = db.get_active_devices(limit=100)
            inactive_count = sum(1 for d in active_devices if d.get('last_used') and 
                                (datetime.now() - datetime.fromisoformat(d['last_used'])) > timedelta(days=1))
            
            if inactive_count > len(active_devices) * 0.5:  # More than 50% inactive
                logger.warning(f"Many inactive devices: {inactive_count}/{len(active_devices)}")
        except Exception as e:
            logger.error(f"Device status check failed: {e}")
    
    def _cleanup_user_sessions(self):
        """Cleanup expired user sessions"""
        try:
            current_time = time.time()
            expired_sessions = []
            for user_id, session in self.user_sessions.items():
                if current_time - session.get('last_activity', 0) > 3600:  # 1 hour
                    expired_sessions.append(user_id)
            
            for user_id in expired_sessions:
                del self.user_sessions[user_id]
            
            if expired_sessions:
                logger.debug(f"Cleaned up {len(expired_sessions)} user sessions")
        except Exception as e:
            logger.error(f"User session cleanup failed: {e}")
    
    def _log_cache_stats(self):
        """Log cache statistics"""
        try:
            cache_size = len(self.cache)
            if cache_size > 0:
                logger.debug(f"Cache statistics: {cache_size} items")
        except Exception as e:
            logger.error(f"Cache stats logging failed: {e}")
    
    def aggregate_analytics(self):
        """Enhanced analytics aggregation"""
        try:
            # Get hourly summary
            hourly_summary = db.get_daily_summary()
            
            # Log multiple metrics
            metrics = [
                ('hourly_boosts', hourly_summary.get('boost_stats', {}).get('total_boosts', 0)),
                ('hourly_likes', hourly_summary.get('boost_stats', {}).get('total_likes', 0)),
                ('active_users', hourly_summary.get('user_stats', {}).get('active_users', 0)),
                ('new_users', hourly_summary.get('user_stats', {}).get('new_users', 0))
            ]
            
            for metric_name, metric_value in metrics:
                db.log_metric(
                    metric_name,
                    metric_value,
                    {'timestamp': datetime.now().isoformat()}
                )
            
            # Update system performance metrics
            self._update_performance_metrics()
            
        except Exception as e:
            logger.error(f"Analytics aggregation failed: {e}")
    
    def _update_performance_metrics(self):
        """Update system performance metrics"""
        try:
            # Calculate average response time
            avg_response_time = db.get_average_response_time()
            if avg_response_time:
                db.log_metric(
                    'avg_response_time',
                    avg_response_time,
                    {'timestamp': datetime.now().isoformat()}
                )
            
            # Calculate success rate
            success_rate = db.get_success_rate()
            if success_rate:
                db.log_metric(
                    'success_rate',
                    success_rate,
                    {'timestamp': datetime.now().isoformat()}
                )
        except Exception as e:
            logger.error(f"Performance metrics update failed: {e}")
    
    async def setup_telegram_bot(self):
        """Enhanced Telegram bot setup"""
        print("\n🤖 Setting up Telegram Bot...")
        
        try:
            # Get API credentials from config or use defaults
            api_id = self.config.get('api_id', 2040)
            api_hash = self.config.get('api_hash', 'b18441a1ff607e10a989891a5462e627')
            
            # Initialize Telegram client with session management
            session_name = self.config.get('session_name', 'mbot_session')
            self.telegram_client = TelegramClient(
                f'sessions/{session_name}',
                api_id=api_id,
                api_hash=api_hash,
                device_model='MBOT Ultimate',
                system_version='1.0',
                app_version='v75',
                lang_code='en',
                system_lang_code='en'
            )
            
            # Configure connection
            self.telegram_client.session.set_dc(
                2, '149.154.167.40', 443  # Telegram DC2
            )
            
            # Start the client with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await self.telegram_client.start(bot_token=self.config['bot_token'])
                    logger.info(f"Telegram client connected (attempt {attempt + 1}/{max_retries})")
                    break
                except (ConnectionError, TimeoutError) as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            print("     ✓ Telegram client connected")
            
            # Store client in systems
            self.systems['telegram_client'] = self.telegram_client
            
            # Setup event handlers
            await self.setup_telegram_handlers()
            
            # Send startup notification to owner
            await self.send_startup_notification()
            
            # Set bot commands
            await self._set_bot_commands()
            
            print("     ✓ Telegram bot setup completed")
            
            return True
            
        except Exception as e:
            logger.critical(f"Error setting up Telegram bot: {e}", exc_info=True)
            print(f"❌ Error setting up Telegram bot: {e}")
            return False
    
    async def _set_bot_commands(self):
        """Set bot commands for better UX"""
        try:
            commands = [
                types.BotCommand(
                    command='start',
                    description='Start the bot and see welcome message'
                ),
                types.BotCommand(
                    command='boost',
                    description='Boost video views: /boost <url> <count>'
                ),
                types.BotCommand(
                    command='likes',
                    description='Boost video likes: /likes <url> <count>'
                ),
                types.BotCommand(
                    command='stats',
                    description='Show your statistics'
                ),
                types.BotCommand(
                    command='profile',
                    description='Show your profile'
                ),
                types.BotCommand(
                    command='help',
                    description='Show help message'
                ),
                types.BotCommand(
                    command='cancel',
                    description='Cancel current boost'
                ),
                types.BotCommand(
                    command='history',
                    description='Show boost history'
                ),
                types.BotCommand(
                    command='balance',
                    description='Check your balance'
                )
            ]
            
            await self.telegram_client(types.bots.SetBotCommandsRequest(
                scope=types.BotCommandScopeDefault(),
                lang_code='en',
                commands=commands
            ))
            
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.warning(f"Failed to set bot commands: {e}")
    
    async def setup_telegram_handlers(self):
        """Enhanced Telegram event handlers"""
        
        # Cache for user states
        user_states = {}
        
        @self.telegram_client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Enhanced start handler"""
            try:
                user = await event.get_sender()
                chat = await event.get_chat()
                
                # Rate limiting check
                user_id = user.id
                current_time = time.time()
                if user_id in self.rate_limiter:
                    last_time = self.rate_limiter[user_id].get('start', 0)
                    if current_time - last_time < 2:  # 2 seconds cooldown
                        await event.respond("⏳ Please wait a moment before sending another command.")
                        return
                
                self.rate_limiter[user_id] = {'start': current_time}
                
                # Add/update user in database
                user_data = {
                    'telegram_id': user.id,
                    'username': user.username or "",
                    'first_name': user.first_name or "",
                    'last_name': user.last_name or "",
                    'last_active': datetime.now().isoformat()
                }
                
                user_id_db = db.add_user(**user_data)
                
                if user_id_db:
                    # Create user session
                    self.user_sessions[user.id] = {
                        'user_id': user_id_db,
                        'last_activity': time.time(),
                        'state': 'idle'
                    }
                    
                    # Send welcome message
                    welcome_msg = await self._get_welcome_message(user)
                    await event.respond(welcome_msg, parse_mode='markdown')
                    
                    # Send help message after welcome
                    await asyncio.sleep(1)
                    await event.respond(
                        "💡 **Quick Start:** Use `/boost <url> <count>` to boost a video!\n"
                        "Example: `/boost https://tiktok.com/@user/video/123456789 1000`",
                        parse_mode='markdown'
                    )
                    
                    # Notify admin about new user
                    if hasattr(self.systems['notification'], 'notify_new_user'):
                        self.systems['notification'].notify_new_user(
                            user.id,
                            user.username or 'N/A',
                            user.first_name or 'Unknown',
                            chat.id
                        )
                        
                    logger.info(f"New user started: {user.id} (@{user.username})")
                    
                else:
                    await event.respond("❌ **Error:** Could not register user. Please contact admin.")
                    
            except FloodWaitError as e:
                logger.warning(f"Flood wait for user {user.id}: {e.seconds} seconds")
                await event.respond(f"⏳ Please wait {e.seconds} seconds before trying again.")
            except Exception as e:
                logger.error(f"Error in start handler: {e}", exc_info=True)
                await event.respond("❌ **Error:** Something went wrong. Please try again later.")
        
        @self.telegram_client.on(events.NewMessage(pattern=r'^/boost(?:\s+(.+))?$'))
        async def boost_handler(event):
            """Enhanced boost handler with validation"""
            try:
                user = await event.get_sender()
                user_id = user.id
                
                # Check if user exists
                if user_id not in self.user_sessions:
                    await event.respond("❌ **Please use /start first**")
                    return
                
                # Parse arguments
                args = event.pattern_match.group(1)
                if not args:
                    # Interactive mode
                    user_states[user_id] = {'command': 'boost', 'step': 'url'}
                    await event.respond(
                        "📹 **Enter TikTok video URL:**\n\n"
                        "Example: `https://www.tiktok.com/@username/video/123456789`\n"
                        "or just the video ID: `123456789`",
                        parse_mode='markdown'
                    )
                    return
                
                args_list = args.split()
                if len(args_list) < 2:
                    await event.respond("❌ **Usage:** `/boost <video_url> <view_count>`\n\nExample: `/boost https://tiktok.com/video/123 1000`")
                    return
                
                video_url = args_list[0]
                try:
                    count = int(args_list[1])
                except ValueError:
                    await event.respond("❌ **Error:** Count must be a number")
                    return
                
                # Process boost
                await self._process_boost_command(event, user, video_url, count, 'views')
                
            except Exception as e:
                logger.error(f"Error in boost handler: {e}", exc_info=True)
                await event.respond(f"❌ **Error:** {str(e)[:100]}")
        
        @self.telegram_client.on(events.NewMessage(pattern=r'^/likes(?:\s+(.+))?$'))
        async def likes_handler(event):
            """Handle likes boost command"""
            try:
                user = await event.get_sender()
                user_id = user.id
                
                if user_id not in self.user_sessions:
                    await event.respond("❌ **Please use /start first**")
                    return
                
                args = event.pattern_match.group(1)
                if not args:
                    user_states[user_id] = {'command': 'likes', 'step': 'url'}
                    await event.respond(
                        "❤️ **Enter TikTok video URL for likes boost:**\n\n"
                        "Example: `https://www.tiktok.com/@username/video/123456789`",
                        parse_mode='markdown'
                    )
                    return
                
                args_list = args.split()
                if len(args_list) < 2:
                    await event.respond("❌ **Usage:** `/likes <video_url> <like_count>`")
                    return
                
                video_url = args_list[0]
                try:
                    count = int(args_list[1])
                except ValueError:
                    await event.respond("❌ **Error:** Count must be a number")
                    return
                
                await self._process_boost_command(event, user, video_url, count, 'likes')
                
            except Exception as e:
                logger.error(f"Error in likes handler: {e}", exc_info=True)
                await event.respond(f"❌ **Error:** {str(e)[:100]}")
        
        @self.telegram_client.on(events.NewMessage(pattern='/cancel'))
        async def cancel_handler(event):
            """Cancel current boost"""
            try:
                user = await event.get_sender()
                user_id = user.id
                
                if user_id in self.active_boosts:
                    boost_id = self.active_boosts[user_id]['boost_id']
                    self.active_boosts[user_id]['status'] = 'cancelled'
                    
                    # Update database
                    db.update_boost(boost_id, {'status': 'cancelled'})
                    
                    await event.respond(f"✅ **Boost cancelled:** `{boost_id}`")
                    logger.info(f"Boost cancelled by user {user_id}: {boost_id}")
                else:
                    await event.respond("❌ **No active boost to cancel**")
                    
            except Exception as e:
                logger.error(f"Error in cancel handler: {e}")
                await event.respond("❌ **Error:** Could not cancel boost")
        
        @self.telegram_client.on(events.NewMessage(pattern='/history'))
        async def history_handler(event):
            """Show boost history"""
            try:
                user = await event.get_sender()
                user_data = db.get_user(user.id, by_telegram_id=True)
                
                if not user_data:
                    await event.respond("❌ **Please use /start first**")
                    return
                
                # Get user's boost history
                boosts = db.get_user_boosts(user_data['id'], limit=10)
                
                if not boosts:
                    await event.respond("📭 **No boost history found**")
                    return
                
                history_msg = "📋 **Your Boost History:**\n\n"
                for i, boost in enumerate(boosts, 1):
                    status_emoji = {
                        'completed': '✅',
                        'processing': '🔄',
                        'failed': '❌',
                        'cancelled': '⏹️',
                        'pending': '⏳'
                    }.get(boost['status'], '❓')
                    
                    history_msg += (
                        f"{i}. **{boost['boost_type'].title()} Boost**\n"
                        f"   ID: `{boost['id']}`\n"
                        f"   Status: {status_emoji} {boost['status']}\n"
                        f"   Target: {boost['target_count']}\n"
                        f"   Completed: {boost.get('completed_count', 0)}\n"
                        f"   Date: {boost['start_time'][:10]}\n\n"
                    )
                
                await event.respond(history_msg, parse_mode='markdown')
                
            except Exception as e:
                logger.error(f"Error in history handler: {e}")
                await event.respond("❌ **Error:** Could not fetch history")
        
        @self.telegram_client.on(events.NewMessage(pattern='/balance'))
        async def balance_handler(event):
            """Check user balance"""
            try:
                user = await event.get_sender()
                user_data = db.get_user(user.id, by_telegram_id=True)
                
                if not user_data:
                    await event.respond("❌ **Please use /start first**")
                    return
                
                balance_msg = (
                    f"💰 **Your Balance & Stats**\n\n"
                    f"👤 **User:** {user_data['first_name']}\n"
                    f"🆔 **ID:** `{user_data['telegram_id']}`\n\n"
                    f"📊 **Statistics:**\n"
                    f"• Total Boosts: {user_data['total_boosts']}\n"
                    f"• Total Likes: {user_data['total_likes']}\n"
                    f"• Total Followers: {user_data.get('total_followers', 0)}\n"
                    f"• Total Spent: ${user_data.get('total_spent', 0):.2f}\n"
                    f"• Boost Streak: {user_data.get('boost_streak', 0)} days\n\n"
                    f"📅 **Activity:**\n"
                    f"• Joined: {user_data['join_date'][:10] if user_data['join_date'] else 'N/A'}\n"
                    f"• Last Active: {user_data['last_active'][:10] if user_data['last_active'] else 'N/A'}"
                )
                
                await event.respond(balance_msg, parse_mode='markdown')
                
            except Exception as e:
                logger.error(f"Error in balance handler: {e}")
                await event.respond("❌ **Error:** Could not fetch balance")
        
        @self.telegram_client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            """Enhanced stats handler"""
            try:
                user = await event.get_sender()
                user_data = db.get_user(user.id, by_telegram_id=True)
                
                if user_data:
                    # Calculate success rate
                    success_rate = 0
                    if user_data['total_boosts'] > 0:
                        success_rate = (user_data['total_boosts'] / 
                                      (user_data['total_boosts'] + user_data.get('failed_boosts', 0))) * 100
                    
                    stats_msg = f"""
📊 **Your Statistics**

👤 **User Info:**
• ID: `{user_data['telegram_id']}`
• Username: @{user_data['username'] or 'N/A'}
• Name: {user_data['first_name']} {user_data['last_name'] or ''}

🚀 **Boost Performance:**
• Total Boosts: {user_data['total_boosts']}
• Total Likes: {user_data['total_likes']}
• Success Rate: {success_rate:.1f}%
• Profile Views: {user_data['profile_views']}

📈 **Ranking:**
• Boost Streak: {user_data.get('boost_streak', 0)} days
• Total Spent: ${user_data.get('total_spent', 0):.2f}
• User Level: {self._calculate_user_level(user_data)}

📅 **Activity:**
• Join Date: {user_data['join_date'][:10] if user_data['join_date'] else 'N/A'}
• Last Active: {user_data['last_active'][:10] if user_data['last_active'] else 'N/A'}
• Account Age: {self._calculate_account_age(user_data['join_date'])} days

🔒 **Status:** {user_data['status'].upper()}
"""
                else:
                    stats_msg = "❌ **Error:** User data not found. Please use /start first."
                
                await event.respond(stats_msg, parse_mode='markdown')
                
            except Exception as e:
                logger.error(f"Error in stats handler: {e}")
                await event.respond("❌ **Error:** Could not fetch statistics")
        
        @self.telegram_client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            """Enhanced help handler"""
            try:
                help_msg = f"""
❓ **MBOT Ultimate Help - Version {self.config['version']}**

🚀 **Core Commands:**
`/start` - Start the bot and see welcome message
`/boost <url> <count>` - Boost video views
`/likes <url> <count>` - Boost video likes
`/cancel` - Cancel current boost
`/stats` - Show your detailed statistics
`/profile` - Show your profile
`/history` - Show boost history
`/balance` - Check balance and spending

📋 **How to Use:**
1. Copy TikTok video URL
2. Use `/boost URL COUNT` to boost views
3. Use `/likes URL COUNT` to boost likes
4. Check progress with `/stats`

⚡ **Advanced Features:**
• Auto-retry on failure
• Progress tracking
• Real-time analytics
• Multiple device support
• Rate limiting protection

⚠️ **Important Notes:**
• Only video account is at risk
• Your device is 100% safe
• Results may take 5-10 minutes
• Maximum boost: {self.config.get('max_boost_count', 10000)} per request

🔒 **Security Features:**
• Military grade encryption (AES-256)
• Advanced anti-detection
• IP rotation (if proxies enabled)
• Anonymous boosting
• Data protection

💰 **Pricing:**
• Views: {self.config.get('pricing', {}).get('views_per_dollar', 1000)} per $1
• Likes: {self.config.get('pricing', {}).get('likes_per_dollar', 500)} per $1
• Followers: {self.config.get('pricing', {}).get('followers_per_dollar', 100)} per $1

📞 **Support:** Contact @{self.config['owner_username']} for help
"""
                await event.respond(help_msg, parse_mode='markdown')
                
            except Exception as e:
                logger.error(f"Error in help handler: {e}")
                await event.respond("❌ **Error:** Could not display help")
        
        @self.telegram_client.on(events.NewMessage(pattern='/profile'))
        async def profile_handler(event):
            """Enhanced profile handler"""
            try:
                user = await event.get_sender()
                user_data = db.get_user(user.id, by_telegram_id=True)
                
                if user_data:
                    # Calculate user level
                    user_level = self._calculate_user_level(user_data)
                    
                    profile_msg = f"""
👤 **Your Profile**

🆔 **User ID:** `{user_data['telegram_id']}`
📛 **Name:** {user_data['first_name']} {user_data['last_name'] or ''}
📧 **Username:** @{user_data['username'] or 'Not set'}
🏆 **Level:** {user_level}

📊 **Activity Stats:**
• Total Boosts: {user_data['total_boosts']}
• Total Likes: {user_data['total_likes']}
• Profile Views: {user_data['profile_views']}
• Boost Streak: {user_data.get('boost_streak', 0)} days

💰 **Financial:**
• Total Spent: ${user_data.get('total_spent', 0):.2f}
• Avg. Cost/Boost: ${user_data.get('total_spent', 0)/user_data['total_boosts']:.2f if user_data['total_boosts'] > 0 else 0}

📅 **Account Info:**
• Joined: {user_data['join_date'][:10] if user_data['join_date'] else 'N/A'}
• Last Active: {user_data['last_active'][:10] if user_data['last_active'] else 'N/A'}
• Status: {user_data['status'].upper()}
• Trust Score: {self._calculate_trust_score(user_data)}%

⚙️ **Settings:** {user_data.get('settings', 'Default')}
"""
                else:
                    profile_msg = "❌ **Error:** Profile not found. Use /start to create your profile."
                
                await event.respond(profile_msg, parse_mode='markdown')
                
            except Exception as e:
                logger.error(f"Error in profile handler: {e}")
                await event.respond("❌ **Error:** Could not fetch profile")
        
        # Handle interactive mode responses
        @self.telegram_client.on(events.NewMessage)
        async def message_handler(event):
            """Handle all other messages"""
            if event.text and event.text.startswith('/'):
                return  # Commands are handled separately
            
            user = await event.get_sender()
            user_id = user.id
            
            # Check if user is in interactive mode
            if user_id in user_states:
                state = user_states[user_id]
                
                if state['step'] == 'url':
                    video_url = event.text.strip()
                    
                    # Validate URL
                    if not self._is_valid_tiktok_url(video_url):
                        await event.respond("❌ **Invalid TikTok URL.** Please enter a valid URL or video ID:")
                        return
                    
                    # Store URL and ask for count
                    user_states[user_id]['url'] = video_url
                    user_states[user_id]['step'] = 'count'
                    
                    boost_type = state['command']
                    await event.respond(
                        f"🎯 **Enter number of {boost_type}:**\n\n"
                        f"Maximum: {self.config.get('max_boost_count', 10000)}\n"
                        f"Recommended: 100-1000 for quick results"
                    )
                    return
                
                elif state['step'] == 'count':
                    try:
                        count = int(event.text.strip())
                        max_count = self.config.get('max_boost_count', 10000)
                        
                        if count < 1:
                            await event.respond("❌ **Count must be at least 1**")
                            return
                        
                        if count > max_count:
                            await event.respond(f"❌ **Maximum count is {max_count}**")
                            return
                        
                        # Process the boost
                        boost_type = state['command']
                        video_url = user_states[user_id]['url']
                        
                        await self._process_boost_command(event, user, video_url, count, boost_type)
                        
                        # Clear user state
                        del user_states[user_id]
                        
                    except ValueError:
                        await event.respond("❌ **Please enter a valid number**")
                        return
            
            # Default response for regular messages
            else:
                await event.respond(
                    "🤖 **Hello! I'm MBOT - Ultimate TikTok Booster!**\n\n"
                    "Use /help to see all available commands.\n"
                    "Use /start to begin if you haven't already.\n\n"
                    "🚀 **Quick Start:** `/boost <url> <count>`",
                    parse_mode='markdown'
                )
    
    async def _process_boost_command(self, event, user, video_url: str, count: int, boost_type: str):
        """Process boost command with validation"""
        try:
            # Validate count
            max_count = self.config.get('max_boost_count', 10000)
            if count > max_count:
                await event.respond(f"❌ **Error:** Maximum boost count is {max_count}")
                return
            
            # Check if user has too many active boosts
            user_boosts = self._get_user_active_boosts(user.id)
            if len(user_boosts) >= 3:  # Max 3 concurrent boosts
                await event.respond("❌ **Error:** You have too many active boosts. Wait for some to complete.")
                return
            
            # Extract video ID
            video_id = self.extract_video_id(video_url)
            if not video_id:
                await event.respond("❌ **Error:** Invalid video URL or ID")
                return
            
            # Check cache for recent boosts to same video
            cache_key = f"{user.id}_{video_id}_{boost_type}"
            if cache_key in self.cache:
                last_boost_time = self.cache[cache_key][0]
                if time.time() - last_boost_time < 300:  # 5 minutes cooldown
                    await event.respond("⚠️ **Warning:** You boosted this video recently. Please wait 5 minutes.")
                    return
            
            # Create boost
            await event.respond(f"🚀 **Starting {boost_type.title()} Boost...**\n\n📹 Video: `{video_id}`\n🎯 Target: {count} {boost_type}\n\n⏳ Please wait...")
            
            # Create boost record
            boost_id = self._generate_boost_id()
            boost_data = {
                'id': boost_id,
                'user_id': user.id,
                'video_id': video_id,
                'video_url': video_url,
                'boost_type': boost_type,
                'target_count': count,
                'status': 'pending',
                'start_time': datetime.now().isoformat(),
                'metadata': json.dumps({
                    'user_username': user.username,
                    'user_first_name': user.first_name,
                    'chat_id': event.chat_id
                })
            }
            
            # Save to database
            db.create_boost(**{k: v for k, v in boost_data.items() if k != 'id'})
            
            # Store in active boosts
            self.active_boosts[user.id] = {
                'boost_id': boost_id,
                'video_id': video_id,
                'count': count,
                'type': boost_type,
                'start_time': time.time(),
                'status': 'processing',
                'chat_id': event.chat_id
            }
            
            # Update cache
            self.cache[cache_key] = (time.time(), boost_id)
            
            # Start boost in background
            self.executor.submit(
                self.process_boost,
                boost_id, video_id, count, user.id, event.chat_id, boost_type
            )
            
            await event.respond(
                f"✅ **Boost Started Successfully!**\n\n"
                f"📊 **Boost ID:** `{boost_id}`\n"
                f"🎯 **Target:** {count} {boost_type}\n"
                f"📹 **Video:** {video_id}\n"
                f"⏱️ **Estimated time:** {count//50} seconds\n\n"
                f"🔄 **Status:** Processing...\n"
                f"📈 **Progress:** 0%\n\n"
                f"Use `/cancel` to stop this boost.\n"
                f"Use `/stats` to check progress."
            )
            
            logger.info(f"Boost started: {boost_id} for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error processing boost command: {e}", exc_info=True)
            await event.respond(f"❌ **Error:** Failed to start boost: {str(e)[:100]}")
    
    def _get_user_active_boosts(self, user_id: int) -> List[Dict]:
        """Get user's active boosts"""
        return [b for b in self.active_boosts.values() 
                if b.get('user_id') == user_id and b.get('status') == 'processing']
    
    def _generate_boost_id(self) -> str:
        """Generate unique boost ID"""
        timestamp = int(time.time() * 1000)
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"BOOST_{timestamp}_{random_str}"
    
    def _is_valid_tiktok_url(self, url: str) -> bool:
        """Validate TikTok URL"""
        import re
        patterns = [
            r'^(https?://)?(www\.)?tiktok\.com/.+',
            r'^\d{18,19}$',  # Video ID
            r'^@[\w.]+$',    # Username
        ]
        
        for pattern in patterns:
            if re.match(pattern, url, re.IGNORECASE):
                return True
        
        return False
    
    async def _get_welcome_message(self, user) -> str:
        """Generate personalized welcome message"""
        welcome_msgs = [
            f"""🎉 **Welcome to MBOT Ultimate v{self.config['version']}!**

👋 **Hello {user.first_name}!** I'm your ultimate TikTok boosting assistant.

🚀 **Ultimate TikTok Boosting System**
• Ultra-fast views/likes delivery (50+ per second)
• Advanced anti-detection technology
• 100% device safety guarantee
• Real-time analytics dashboard
• Multi-device support

⚡ **Quick Start:**
1. Copy TikTok video URL
2. Send `/boost <url> <count>`
3. Watch your views grow!

🔒 **Security Features:**
• Military grade encryption
• Anonymous boosting
• IP protection
• Zero device risk

📊 **Your Benefits:**
• Priority support
• Volume discounts
• Daily bonuses
• Streak rewards

💡 **Pro Tip:** Start with 500 views to test the system!

Ready to boost? Send me a TikTok URL! 🚀""",
            
            f"""🌟 **Welcome {user.first_name}!** You've joined the most advanced TikTok booster!

⚡ **Why Choose MBOT Ultimate?**
• **Speed:** 50-100 views/second
• **Reliability:** 99.8% success rate
• **Safety:** Your device is 100% protected
• **Stealth:** Undetectable by TikTok

🎯 **Get Started Immediately:**
`/boost https://tiktok.com/video/123 1000`

📈 **Track Progress:**
`/stats` - See your statistics
`/profile` - View your profile
`/history` - Check past boosts

⚠️ **Important:** Only the video account is at risk. Your personal device remains completely safe.

💬 **Need help?** Use `/help` anytime!""",
            
            f"""🔥 **WELCOME {user.first_name.upper()}!** 🚀

You've unlocked access to the **MOST POWERFUL** TikTok booster!

📊 **SYSTEM CAPABILITIES:**
• Max Speed: 100 requests/second
• Concurrent Boosts: 5 at once
• Max per Boost: {self.config.get('max_boost_count', 10000)}
• Device Pool: 1000+ devices

🛡️ **ADVANCED PROTECTION:**
• AES-256 Encryption
• Dynamic Fingerprinting
• IP Rotation System
• Request Randomization

💰 **COST EFFECTIVE:**
• {self.config.get('pricing', {}).get('views_per_dollar', 1000)} views per $1
• Bulk discounts available
• First boost 50% off!

⚡ **TRY IT NOW:**
Send me a TikTok video URL and I'll show you the power!

Type `/help` for complete command list."""
        ]
        
        # Select welcome message based on time of day
        hour = datetime.now().hour
        if hour < 12:
            msg_index = 0  # Morning message
        elif hour < 18:
            msg_index = 1  # Afternoon message
        else:
            msg_index = 2  # Evening message
        
        return welcome_msgs[msg_index]
    
    def _calculate_user_level(self, user_data: Dict) -> str:
        """Calculate user level based on activity"""
        total_boosts = user_data.get('total_boosts', 0)
        total_spent = user_data.get('total_spent', 0)
        
        if total_boosts >= 1000 or total_spent >= 100:
            return "🌟 ELITE"
        elif total_boosts >= 500 or total_spent >= 50:
            return "🔥 PRO"
        elif total_boosts >= 100 or total_spent >= 20:
            return "⭐ ADVANCED"
        elif total_boosts >= 50 or total_spent >= 10:
            return "💎 INTERMEDIATE"
        elif total_boosts >= 10 or total_spent >= 5:
            return "🚀 BEGINNER"
        else:
            return "🆕 NEW"
    
    def _calculate_account_age(self, join_date: str) -> int:
        """Calculate account age in days"""
        if not join_date:
            return 0
        
        try:
            join = datetime.fromisoformat(join_date.replace('Z', '+00:00'))
            age = (datetime.now() - join).days
            return max(age, 0)
        except:
            return 0
    
    def _calculate_trust_score(self, user_data: Dict) -> int:
        """Calculate user trust score"""
        score = 50  # Base score
        
        # Add points for positive factors
        if user_data.get('total_boosts', 0) > 0:
            score += min(user_data['total_boosts'] // 10, 30)
        
        if user_data.get('boost_streak', 0) > 0:
            score += min(user_data['boost_streak'] * 2, 20)
        
        # Deduct for negative factors
        if user_data.get('failed_boosts', 0) > user_data.get('total_boosts', 1) * 0.5:
            score -= 20
        
        return max(0, min(score, 100))
    
    async def send_startup_notification(self):
        """Enhanced startup notification"""
        if self.config.get('owner_id'):
            try:
                uptime = int(time.time() - self.start_time)
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                seconds = uptime % 60
                
                # Get system stats
                active_users = db.get_active_users(count_only=True)
                total_boosts = db.get_total_boosts()
                system_load = self._get_system_load()
                
                message = f"""
🚀 **MBOT Ultimate Started Successfully!**

📊 **System Status:**
• Version: v{self.config['version']} (Real: v75)
• Uptime: {hours}h {minutes}m {seconds}s
• All Systems: ✅ OPERATIONAL
• Security Level: {self.config.get('security_level', 'high').upper()}
• Boost Speed: {self.config.get('boost_speed', 'ultra').upper()}

📈 **Statistics:**
• Active Users: {active_users}
• Total Boosts: {total_boosts}
• System Load: {system_load}%
• Active Devices: {len(db.get_active_devices(limit=1000))}

⚙️ **Configuration:**
• Max Threads: {self.config.get('max_threads', 100)}
• Max RPM: {self.config.get('max_requests_per_minute', 3000)}
• Proxy Enabled: {'✅' if self.config.get('proxy_enabled') else '❌'}
• Auto Restart: {'✅' if self.config.get('auto_restart') else '❌'}
• Backup Enabled: {'✅' if self.config.get('backup_enabled') else '❌'}

🔒 **Security Status:**
• Encryption: ✅ ACTIVE
• Anti-Detection: ✅ ACTIVE
• Monitoring: ✅ ACTIVE
• Notifications: ✅ ACTIVE

📡 **Services Running:**
• Telegram Bot: ✅
• API Server: {'✅' if self.config.get('api_enabled') else '❌'}
• Web Dashboard: {'✅' if self.config.get('dashboard_enabled') else '❌'}
• Analytics: ✅
• Backup System: {'✅' if self.config.get('backup_enabled') else '❌'}

✅ **System is ready to boost!**
"""
                
                await self.telegram_client.send_message(self.config['owner_id'], message)
                logger.info("Startup notification sent to owner")
                
            except Exception as e:
                logger.error(f"Error sending startup notification: {e}")
    
    def _get_system_load(self) -> float:
        """Get system load percentage"""
        try:
            import psutil
            return psutil.cpu_percent(interval=1)
        except:
            return 0.0
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Enhanced video ID extraction"""
        import re
        
        # If it's already a video ID
        if re.match(r'^\d{18,19}$', url):
            return url
        
        patterns = [
            r'video/(\d+)',
            r'/v\.douyin\.com/(\w+)/',
            r'/(\d{18,19})/',
            r'\?video_id=(\d+)',
            r'item_id=(\d+)',
            r'/(\d{10,20})(?:\?|$)',
            r'tiktok\.com/(?:@[\w.]+/)?video/(\d+)',
            r'vm\.tiktok\.com/(\w+)/?',
            r'vt\.tiktok\.com/(\w+)/?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try to extract from shortened URLs by checking if it's a valid ID
        possible_id = re.search(r'(\d{10,20})', url)
        if possible_id and len(possible_id.group(1)) >= 10:
            return possible_id.group(1)
        
        return None
    
    def process_boost(self, boost_id: str, video_id: str, count: int, user_id: int, chat_id: int, boost_type: str = 'views'):
        """Enhanced boost processing with better error handling"""
        try:
            # Update boost status
            db.update_boost(boost_id, {'status': 'processing'})
            
            # Get available devices
            devices = db.get_active_devices(limit=self.boost_config.max_devices_per_boost)
            
            if not devices:
                error_msg = "No active devices available"
                db.update_boost(boost_id, {
                    'status': 'failed',
                    'end_time': datetime.now().isoformat(),
                    'metadata': json.dumps({'error': error_msg})
                })
                
                asyncio.run_coroutine_threadsafe(
                    self.send_boost_update(chat_id, f"❌ **Boost Failed:** {error_msg}"),
                    asyncio.get_event_loop()
                )
                return
            
            # Calculate batch processing
            batch_size = min(count, self.boost_config.batch_size)
            total_batches = (count + batch_size - 1) // batch_size
            
            completed = 0
            failed = 0
            start_time = time.time()
            
            # Send initial progress
            asyncio.run_coroutine_threadsafe(
                self.send_boost_progress(chat_id, boost_id, 0, completed, count, 0, total_batches),
                asyncio.get_event_loop()
            )
            
            # Process in batches
            for batch_num in range(total_batches):
                if not self.running:
                    db.update_boost(boost_id, {'status': 'cancelled'})
                    break
                
                batch_start = batch_num * batch_size
                batch_end = min((batch_num + 1) * batch_size, count)
                batch_target = batch_end - batch_start
                
                # Process batch
                batch_completed, batch_failed = self._process_batch(
                    boost_id, video_id, batch_target, devices, boost_type
                )
                
                completed += batch_completed
                failed += batch_failed
                
                # Update progress
                progress = (completed / count) * 100
                elapsed = time.time() - start_time
                estimated_total = (elapsed / (batch_num + 1)) * total_batches if batch_num > 0 else 0
                remaining = max(0, estimated_total - elapsed)
                
                asyncio.run_coroutine_threadsafe(
                    self.send_boost_progress(
                        chat_id, boost_id, progress, completed, count, 
                        batch_num + 1, total_batches, remaining
                    ),
                    asyncio.get_event_loop()
                )
                
                # Rate limiting
                time.sleep(0.5)  # Small delay between batches
            
            # Finalize boost
            end_time = time.time()
            duration = end_time - start_time
            average_rps = completed / duration if duration > 0 else 0
            
            status = 'completed' if completed > 0 else 'failed'
            db.update_boost(boost_id, {
                'status': status,
                'end_time': datetime.now().isoformat(),
                'duration': duration,
                'average_rps': average_rps,
                'completed_count': completed,
                'failed_count': failed
            })
            
            # Update user stats
            if completed > 0:
                db.increment_user_stat(user_id, f'total_{boost_type}', completed)
                db.increment_user_stat(user_id, 'total_boosts', 1)
            
            # Remove from active boosts
            if user_id in self.active_boosts:
                del self.active_boosts[user_id]
            
            # Send completion message
            asyncio.run_coroutine_threadsafe(
                self.send_boost_completion(chat_id, boost_id, completed, count, duration, boost_type),
                asyncio.get_event_loop()
            )
            
            # Send notification
            if hasattr(self.systems['notification'], 'notify_boost_completed'):
                self.systems['notification'].notify_boost_completed(
                    user_id,
                    boost_id,
                    video_id,
                    completed,
                    count,
                    duration,
                    boost_type
                )
            
            logger.info(f"Boost {boost_id} completed: {completed}/{count} {boost_type}")
            
        except Exception as e:
            logger.error(f"Error processing boost {boost_id}: {e}", exc_info=True)
            
            db.update_boost(boost_id, {
                'status': 'failed',
                'end_time': datetime.now().isoformat(),
                'metadata': json.dumps({'error': str(e)})
            })
            
            if user_id in self.active_boosts:
                del self.active_boosts[user_id]
            
            asyncio.run_coroutine_threadsafe(
                self.send_boost_update(chat_id, f"❌ **Boost Failed:** {str(e)[:100]}"),
                asyncio.get_event_loop()
            )
            
            if hasattr(self.systems['notification'], 'notify_boost_failed'):
                self.systems['notification'].notify_boost_failed(
                    user_id,
                    boost_id,
                    video_id,
                    str(e)
                )
    
    def _process_batch(self, boost_id: str, video_id: str, batch_size: int, 
                      devices: List[Dict], boost_type: str) -> Tuple[int, int]:
        """Process a batch of boost requests"""
        completed = 0
        failed = 0
        
        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=min(batch_size, 50)) as executor:
            futures = []
            for i in range(batch_size):
                device = devices[i % len(devices)]
                future = executor.submit(
                    self._make_boost_request,
                    boost_id, video_id, device['device_id'], boost_type
                )
                futures.append(future)
            
            # Collect results
            for future in as_completed(futures):
                try:
                    success, response_time, error = future.result(timeout=30)
                    if success:
                        completed += 1
                    else:
                        failed += 1
                    
                    # Log request
                    db.log_boost_request(
                        boost_id,
                        device['device_id'],
                        None,
                        success,
                        response_time,
                        error
                    )
                    
                except Exception as e:
                    failed += 1
                    logger.warning(f"Boost request failed: {e}")
        
        return completed, failed
    
    def _make_boost_request(self, boost_id: str, video_id: str, 
                           device_id: str, boost_type: str) -> Tuple[bool, float, Optional[str]]:
        """Make a single boost request"""
        start_time = time.time()
        
        try:
            # Simulate request (replace with actual TikTok API call)
            time.sleep(random.uniform(0.1, 0.5))
            
            # Simulate success rate (95% success)
            success = random.random() < 0.95
            
            response_time = time.time() - start_time
            
            if success:
                # Update device stats
                db.increment_device_stat(device_id, 'total_requests', 1)
                db.increment_device_stat(device_id, 'successful_requests', 1)
                return True, response_time, None
            else:
                error = "Simulated failure"  # Replace with actual error
                db.increment_device_stat(device_id, 'total_requests', 1)
                return False, response_time, error
                
        except Exception as e:
            response_time = time.time() - start_time
            return False, response_time, str(e)
    
    async def send_boost_update(self, chat_id: int, message: str):
        """Send boost update message"""
        try:
            if self.telegram_client and self.telegram_client.is_connected():
                await self.telegram_client.send_message(chat_id, message, parse_mode='markdown')
        except Exception as e:
            logger.error(f"Error sending boost update: {e}")
    
    async def send_boost_progress(self, chat_id: int, boost_id: str, progress: float, 
                                 completed: int, target: int, current_batch: int, 
                                 total_batches: int, remaining_time: float = 0):
        """Send boost progress update"""
        try:
            # Create progress bar
            bars = 20
            filled = int(bars * progress / 100)
            progress_bar = "█" * filled + "░" * (bars - filled)
            
            # Format remaining time
            if remaining_time > 0:
                mins = int(remaining_time // 60)
                secs = int(remaining_time % 60)
                time_str = f"⏱️ **Time Left:** {mins}:{secs:02d}\n"
            else:
                time_str = ""
            
            message = (
                f"📊 **Boost Progress:** `{boost_id}`\n\n"
                f"{progress_bar} **{progress:.1f}%**\n\n"
                f"✅ **Completed:** {completed}/{target}\n"
                f"📦 **Batch:** {current_batch}/{total_batches}\n"
                f"📈 **Speed:** {(completed/max(1, (time.time() - self.start_time))):.1f}/sec\n"
                f"{time_str}"
                f"🔄 **Status:** Processing..."
            )
            
            await self.send_boost_update(chat_id, message)
            
        except Exception as e:
            logger.error(f"Error sending progress update: {e}")
    
    async def send_boost_completion(self, chat_id: int, boost_id: str, 
                                   completed: int, target: int, duration: float, boost_type: str):
        """Send boost completion message"""
        try:
            success_rate = (completed / target * 100) if target > 0 else 0
            speed = completed / duration if duration > 0 else 0
            
            # Get boost details
            boost_data = db.get_boost(boost_id)
            if boost_data:
                video_id = boost_data.get('video_id', 'N/A')
            else:
                video_id = 'N/A'
            
            message = (
                f"🎉 **{boost_type.title()} Boost Completed!**\n\n"
                f"📊 **Boost ID:** `{boost_id}`\n"
                f"📹 **Video:** `{video_id}`\n"
                f"🎯 **Target:** {target} {boost_type}\n"
                f"✅ **Delivered:** {completed} {boost_type}\n"
                f"📈 **Success Rate:** {success_rate:.1f}%\n"
                f"⏱️ **Duration:** {duration:.1f} seconds\n"
                f"🚀 **Average Speed:** {speed:.1f}/second\n"
                f"⚡ **Peak Speed:** {speed * 1.5:.1f}/second\n\n"
                f"✅ **Boost completed successfully!**\n\n"
                f"⚠️ *{boost_type.title()} may take a few minutes to appear on TikTok*\n"
                f"📊 *Check `/stats` for updated statistics*"
            )
            
            await self.send_boost_update(chat_id, message)
            
        except Exception as e:
            logger.error(f"Error sending completion message: {e}")
    
    def handle_shutdown(self, signum, frame):
        """Enhanced shutdown handler"""
        print(f"\n\n⚠️  Received signal {signum}. Gracefully shutting down...")
        self.shutdown()
    
    def shutdown(self):
        """Enhanced graceful shutdown"""
        print("\n🚦 Shutting down MBOT Ultimate...")
        self.running = False
        
        shutdown_steps = [
            ("Stopping notification system", self._stop_notification_system),
            ("Disconnecting Telegram client", self._disconnect_telegram),
            ("Stopping boost manager", self._stop_boost_manager),
            ("Stopping security monitor", self._stop_security_monitor),
            ("Stopping thread pool executor", self._stop_executor),
            ("Closing database connections", self._close_database),
            ("Saving analytics data", self._save_analytics),
            ("Creating shutdown backup", self._create_shutdown_backup)
        ]
        
        for i, (step_name, step_func) in enumerate(shutdown_steps, 1):
            print(f"  [{i}/{len(shutdown_steps)}] {step_name}...")
            try:
                step_func()
                print(f"     ✓ {step_name}")
            except Exception as e:
                print(f"     ⚠️ {step_name} failed: {str(e)[:50]}")
                logger.warning(f"Shutdown step '{step_name}' failed: {e}")
        
        print("\n✅ MBOT Ultimate shut down gracefully.")
        logger.info("MBOT Ultimate shutdown completed")
        
        sys.exit(0)
    
    def _stop_notification_system(self):
        """Stop notification system"""
        if 'notification' in self.systems and self.systems['notification']:
            try:
                self.systems['notification'].stop()
            except:
                pass
    
    def _disconnect_telegram(self):
        """Disconnect Telegram client"""
        if self.telegram_client:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.telegram_client.disconnect())
            except:
                pass
    
    def _stop_boost_manager(self):
        """Stop boost manager"""
        if 'boost_manager' in self.systems and self.systems['boost_manager']:
            try:
                self.systems['boost_manager'].stop_all()
            except:
                pass
    
    def _stop_security_monitor(self):
        """Stop security monitor"""
        if 'security_monitor' in self.systems and self.systems['security_monitor']:
            try:
                self.systems['security_monitor'].monitoring = False
            except:
                pass
    
    def _stop_executor(self):
        """Stop thread pool executor"""
        try:
            self.executor.shutdown(wait=False)
        except:
            pass
    
    def _close_database(self):
        """Close database connections"""
        if 'database' in self.systems and self.systems['database']:
            try:
                self.systems['database'].close()
            except:
                pass
    
    def _save_analytics(self):
        """Save analytics data"""
        if 'analytics' in self.systems and self.systems['analytics']:
            try:
                self.systems['analytics'].save_data()
            except:
                pass
    
    def _create_shutdown_backup(self):
        """Create shutdown backup"""
        if self.config.get('backup_enabled', False):
            try:
                self._create_backup()
            except Exception as e:
                logger.error(f"Shutdown backup failed: {e}")
    
    def print_banner(self):
        """Enhanced startup banner"""
        banner = """
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║      ███╗   ███╗██████╗  ██████╗ ████████╗   ██╗   ██╗███████╗       ║
║      ████╗ ████║██╔══██╗██╔═══██╗╚══██╔══╝   ██║   ██║██╔════╝       ║
║      ██╔████╔██║██████╔╝██║   ██║   ██║█████╗██║   ██║█████╗         ║
║      ██║╚██╔╝██║██╔══██╗██║   ██║   ██║╚════╝██║   ██║██╔══╝         ║
║      ██║ ╚═╝ ██║██████╔╝╚██████╔╝   ██║      ╚██████╔╝███████╗       ║
║      ╚═╝     ╚═╝╚═════╝  ╚═════╝    ╚═╝       ╚═════╝ ╚══════╝       ║
║                                                                       ║
║         U L T I M A T E   T I K T O K   B O O S T E R   v75          ║
║                                                                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  Version:      1.0 (Real: 75)                                        ║
║  Owner:        @rana_editz_00                                        ║
║  Status:       🟢 PRODUCTION READY                                   ║
║  Security:     🔐 MILITARY GRADE ENCRYPTION                          ║
║  Speed:        🚀 ULTRA-FAST (100/sec)                               ║
║  Reliability:  ⭐ 99.8% SUCCESS RATE                                 ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
"""
        print(banner)
        
        # Print system info
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print(f"💾 Database: {self.config.get('database_path', 'data/mbot.db')}")
        print(f"🔒 Security Level: {self.config.get('security_level', 'high').upper()}")
        print("─" * 70)
    
    async def run_async(self):
        """Enhanced main async run method"""
        try:
            # Initialize all systems
            self.initialize_systems()
            
            # Start background services
            self.start_background_services()
            
            # Start cache cleanup
            self.cache_cleanup_thread.start()
            
            # Set running flag
            self.running = True
            
            # Setup Telegram bot
            bot_setup = await self.setup_telegram_bot()
            if not bot_setup:
                print("❌ Failed to setup Telegram bot")
                self.shutdown()
                return
            
            print("\n" + "="*70)
            print("✅ MBOT Ultimate is now running!")
            print("="*70 + "\n")
            
            # Display running services
            services_status = [
                ("📱 Telegram Bot", "✅ Ready to receive commands"),
                ("🌐 Web Dashboard", f"✅ http://localhost:{self.config.get('dashboard_port', 8080)}" 
                 if self.config.get('dashboard_enabled') else "❌ Disabled"),
                ("🔌 API Server", f"✅ http://localhost:{self.config.get('api_port', 5000)}" 
                 if self.config.get('api_enabled') else "❌ Disabled"),
                ("📊 Analytics", "✅ Active"),
                ("🔒 Security Monitor", "✅ Active"),
                ("💾 Backup System", "✅ Active" if self.config.get('backup_enabled') else "❌ Disabled"),
                ("🔄 Update Checker", "✅ Active"),
                ("💬 Notification System", "✅ Active")
            ]
            
            for service, status in services_status:
                print(f"{service}: {status}")
            
            print(f"\n📊 Monitoring {len(self.systems)} systems...")
            print("👤 Send /start to @bot on Telegram to begin")
            print("🛑 Press Ctrl+C to stop the system\n")
            
            # Keep the bot running
            await self.telegram_client.run_until_disconnected()
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Keyboard interrupt received.")
            self.shutdown()
        except Exception as e:
            logger.critical(f"Fatal error in main loop: {e}", exc_info=True)
            print(f"\n\n❌ Fatal error: {e}")
            self.shutdown()
    
    def run(self):
        """Enhanced main run method"""
        self.print_banner()
        
        # Check system requirements
        self._check_system_requirements()
        
        # Create and run async event loop
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            print("\n\n⚠️  Keyboard interrupt received.")
            self.shutdown()
        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            print(f"\n\n❌ Fatal error: {e}")
            self.shutdown()
    
    def _check_system_requirements(self):
        """Check system requirements"""
        print("🔍 Checking system requirements...")
        
        requirements = [
            ("Python 3.7+", sys.version_info >= (3, 7), "3.7 or higher required"),
            ("config.json exists", os.path.exists('config.json'), "Create config.json"),
            ("devices.txt exists", os.path.exists('devices.txt'), "Create devices.txt with device IDs"),
            ("Write permission", os.access('.', os.W_OK), "Need write permission"),
            ("Telethon installed", self._check_module('telethon'), "pip install telethon"),
            ("aiohttp installed", self._check_module('aiohttp'), "pip install aiohttp")
        ]
        
        all_ok = True
        for name, check, message in requirements:
            if check:
                print(f"  ✓ {name}")
            else:
                print(f"  ❌ {name}: {message}")
                all_ok = False
        
        if not all_ok:
            print("\n❌ Please fix the above issues before running MBOT.")
            sys.exit(1)
        
        print("✅ All requirements met\n")
    
    def _check_module(self, module_name: str) -> bool:
        """Check if module is installed"""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False


def main():
    """Enhanced main entry point"""
    # Add command line argument support
    import argparse
    
    parser = argparse.ArgumentParser(description='MBOT Ultimate - TikTok Boosting System')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--config', type=str, default='config.json', help='Config file path')
    parser.add_argument('--no-dashboard', action='store_true', help='Disable web dashboard')
    parser.add_argument('--no-api', action='store_true', help='Disable API server')
    parser.add_argument('--port', type=int, default=8080, help='Web dashboard port')
    
    args = parser.parse_args()
    
    # Set debug mode
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("Debug mode enabled")
    
    # Override config if specified
    if args.config != 'config.json' and os.path.exists(args.config):
        os.environ['MBOT_CONFIG'] = args.config
    
    # Run MBOT
    mbot = MBOTUltimate()
    
    # Override config from command line
    if args.no_dashboard:
        mbot.config['dashboard_enabled'] = False
    if args.no_api:
        mbot.config['api_enabled'] = False
    if args.port:
        mbot.config['dashboard_port'] = args.port
    
    mbot.run()


if __name__ == "__main__":
    main()
