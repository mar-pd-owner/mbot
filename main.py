#!/usr/bin/env python3
"""
MBOT - TikTok Like Bot
Entry Point
"""

import asyncio
import json
import logging
from core_engine import MBotCore
from telegram_interface import MBotTelegram
from utils import setup_logging

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

async def main():
    # Load configuration
    config = load_config()
    
    # Setup logging
    logger = setup_logging(config)
    
    # Initialize core
    core = MBotCore(config)
    
    # Initialize Telegram bot
    telegram_token = config.get('telegram_token')
    if not telegram_token:
        print("❌ Telegram token not found in config.json")
        return
    
    telegram_bot = MBotTelegram(telegram_token, core)
    
    # Start bot
    print("🚀 Starting MBOT...")
    telegram_bot.start()

if __name__ == "__main__":
    asyncio.run(main())
