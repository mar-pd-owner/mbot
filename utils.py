"""
Utility Functions for MBOT
"""

import json
import logging
import time
import hashlib
import random
import string
from typing import Any, Dict, List, Optional
from datetime import datetime
import os

def setup_logging(config: Dict) -> logging.Logger:
    """Setup logging configuration"""
    logger = logging.getLogger('MBOT')
    logger.setLevel(logging.INFO)
    
    # Create handlers
    console_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('mbot.log')
    
    # Create formatters
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set formatters
    console_handler.setFormatter(console_format)
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

def generate_unique_id() -> str:
    """Generate unique ID"""
    timestamp = int(time.time() * 1000)
    random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"{timestamp}_{random_str}"

def calculate_md5(data: str) -> str:
    """Calculate MD5 hash"""
    return hashlib.md5(data.encode()).hexdigest()

def format_time(seconds: float) -> str:
    """Format time in human readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def format_number(number: int) -> str:
    """Format number with commas"""
    return f"{number:,}"

def save_json(data: Dict, filename: str):
    """Save data to JSON file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_json(filename: str) -> Dict:
    """Load data from JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def validate_url(url: str) -> bool:
    """Validate URL format"""
    patterns = [
        'vt.tiktok.com',
        'vm.tiktok.com',
        'tiktok.com/@',
        'tiktok.com/t/'
    ]
    return any(pattern in url for pattern in patterns)

def extract_short_code(url: str) -> Optional[str]:
    """Extract short code from URL"""
    import re
    
    patterns = [
        r'vt\.tiktok\.com/([A-Za-z0-9]+)',
        r'vm\.tiktok\.com/([A-Za-z0-9]+)',
        r'tiktok\.com/t/([A-Za-z0-9]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_file_size(filename: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(filename)
    except:
        return 0

def get_timestamp() -> str:
    """Get current timestamp"""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def create_backup(filename: str):
    """Create backup of file"""
    if os.path.exists(filename):
        backup_name = f"{filename}.backup_{int(time.time())}"
        import shutil
        shutil.copy2(filename, backup_name)
        return backup_name
    return None

def cleanup_old_files(directory: str = ".", pattern: str = "*.backup_*", days: int = 7):
    """Cleanup old backup files"""
    import glob
    import os
    import time
    
    cutoff = time.time() - (days * 24 * 3600)
    
    for filepath in glob.glob(os.path.join(directory, pattern)):
        if os.path.getmtime(filepath) < cutoff:
            os.remove(filepath)

def print_banner():
    """Print MBOT banner"""
    banner = """
╔══════════════════════════════════════╗
║         MBOT ULTIMATE v2.0           ║
║    TikTok Like Bot - Professional    ║
║                                      ║
║  Features:                           ║
║  • 500+ Likes in seconds             ║
║  • Short URL Support                 ║
║  • No Captcha Required               ║
║  • Real Public Likes                 ║
║  • Telegram Bot Interface            ║
║  • Device & Proxy Rotation           ║
║                                      ║
║  GitHub: github.com/mbot-ultimate    ║
╚══════════════════════════════════════╝
    """
    print(banner)

def check_dependencies():
    """Check required dependencies"""
    required = ['telebot', 'aiohttp', 'asyncio', 'requests']
    missing = []
    
    for dep in required:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        print("❌ Missing dependencies:")
        for dep in missing:
            print(f"   - {dep}")
        print("\nInstall with: pip install " + " ".join(missing))
        return False
    
    return True

def bytes_to_human_readable(size: int) -> str:
    """Convert bytes to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"
