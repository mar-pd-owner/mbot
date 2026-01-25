#!/usr/bin/env python3
"""
MBOT - TikTok Like Bot
Fixed Main File
"""

import asyncio
import json
import sys
import os
import time

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_core import MBotCore
from telegram_bot import TelegramBot
from utils import setup_logging

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            print("✅ Config loaded successfully")
            return config
    except FileNotFoundError:
        print("❌ config.json not found!")
        print("Creating default config...")
        
        default_config = {
            "telegram_token": "YOUR_TELEGRAM_BOT_TOKEN",
            "tiktok": {
                "api_endpoints": [
                    "https://api16-normal-c-useast1a.tiktokv.com",
                    "https://api19-normal-c-useast1a.tiktokv.com"
                ],
                "batch_size": 10,
                "max_concurrent": 20,
                "request_timeout": 10
            },
            "devices": {
                "file": "devices.txt",
                "rotation": True,
                "max_devices": 100
            },
            "proxies": {
                "file": "proxies.txt",
                "rotation": True,
                "check_interval": 60
            },
            "limits": {
                "max_likes_per_video": 200,
                "max_videos_per_hour": 20,
                "cooldown_per_video": 2
            }
        }
        
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print("📝 Created config.json - Please edit with your Telegram token")
        return default_config

async def main():
    print("\n" + "="*50)
    print("🚀 MBOT - TikTok Like Bot")
    print("="*50)
    
    # Load configuration
    config = load_config()
    
    # Setup logging
    logger = setup_logging(config)
    logger.info("MBOT Starting...")
    
    # Check Telegram token
    telegram_token = config.get('telegram_token')
    if not telegram_token or telegram_token == "YOUR_TELEGRAM_BOT_TOKEN":
        print("\n❌ ERROR: Telegram token not configured!")
        print("Please edit config.json and add your Telegram Bot Token")
        print("Get token from @BotFather on Telegram")
        print("\nOpen config.json and change:")
        print('"telegram_token": "YOUR_TELEGRAM_BOT_TOKEN"')
        print('to')
        print('"telegram_token": "7123456789:AAHabcdefghijklmnopqrstuvwxyz"')
        return
    
    # Initialize core engine
    print("\n🔧 Initializing MBOT Core...")
    core = MBotCore(config)
    
    # Initialize Telegram bot
    print("🤖 Initializing Telegram Bot...")
    telegram_bot = TelegramBot(telegram_token, core)
    
    print("\n✅ MBOT is ready!")
    print("📱 Send /start to your Telegram bot")
    print("="*50 + "\n")
    
    # Start Telegram bot
    telegram_bot.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 MBOT stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
