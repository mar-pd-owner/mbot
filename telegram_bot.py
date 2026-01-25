"""
Telegram Bot - Fixed Version
"""

import telebot
from telebot import types
import asyncio
import threading
import time
import re

class TelegramBot:
    def __init__(self, token: str, core):
        self.bot = telebot.TeleBot(token)
        self.core = core
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup all bot handlers"""
        
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            welcome_text = """
🤖 *MBOT - TikTok Like Bot* 🤖

*Available Commands:*
/start - Show this message
/like [url] [count] - Send likes to video
/stats - Show bot statistics
/status - Check bot status
/ping - Test if bot is alive

*Usage Examples:*
`/like https://vt.tiktok.com/ZSaf1n2RC/ 100`
`/like https://vm.tiktok.com/ZMRLRsxrK/ 50`

*Notes:*
- Supports vt.tiktok.com and vm.tiktok.com
- Default count is 100 if not specified
- Maximum 200 likes per request
            """
            self.bot.reply_to(message, welcome_text, parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['like'])
        def handle_like(message):
            try:
                # Parse command
                parts = message.text.split()
                if len(parts) < 2:
                    self.bot.reply_to(message, 
                        "❌ *Usage:* `/like [url] [count]`\n"
                        "Example: `/like https://vt.tiktok.com/xxx 100`",
                        parse_mode='Markdown')
                    return
                
                url = parts[1]
                count = int(parts[2]) if len(parts) > 2 else 100
                
                # Validate count
                if count > 200:
                    count = 200
                    self.bot.reply_to(message, "⚠️ Count limited to 200 for stability")
                
                # Validate URL
                if not self.is_valid_tiktok_url(url):
                    self.bot.reply_to(message,
                        "❌ *Invalid URL!*\n"
                        "Please use TikTok short URLs:\n"
                        "- https://vt.tiktok.com/xxx\n"
                        "- https://vm.tiktok.com/xxx",
                        parse_mode='Markdown')
                    return
                
                # Extract video ID
                video_id = self.extract_video_id(url)
                if not video_id:
                    self.bot.reply_to(message, "❌ Could not extract video ID from URL")
                    return
                
                # Send processing message
                processing_msg = self.bot.reply_to(message,
                    f"⏳ *Processing...*\n\n"
                    f"🎯 Video: `{video_id}`\n"
                    f"📊 Target: `{count}` likes\n\n"
                    f"Please wait...",
                    parse_mode='Markdown')
                
                # Process in background thread
                thread = threading.Thread(
                    target=self.process_like_request,
                    args=(message.chat.id, processing_msg.message_id, video_id, count)
                )
                thread.start()
                
            except ValueError:
                self.bot.reply_to(message, "❌ Count must be a number")
            except Exception as e:
                self.bot.reply_to(message, f"❌ Error: {str(e)[:100]}")
        
        @self.bot.message_handler(commands=['stats'])
        def handle_stats(message):
            stats = self.core.get_stats()
            
            stats_text = f"""
📊 *MBOT Statistics*

✅ Total Likes Sent: `{stats['total_likes_sent']:,}`
🎯 Total Videos: `{stats['total_videos']}`
📈 Success Rate: `{stats['overall_success_rate']}`
⏱️ Uptime: `{stats['uptime']}`
🟢 Status: `{stats['bot_status']}`
"""
            self.bot.reply_to(message, stats_text, parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['status'])
        def handle_status(message):
            self.bot.reply_to(message, "🟢 *MBOT Status: ONLINE*\n✅ Bot is running and ready!", parse_mode='Markdown')
        
        @self.bot.message_handler(commands=['ping'])
        def handle_ping(message):
            self.bot.reply_to(message, "🏓 *Pong!* Bot is alive!", parse_mode='Markdown')
    
    def is_valid_tiktok_url(self, url: str) -> bool:
        """Check if URL is a valid TikTok URL"""
        patterns = [
            r'https?://vt\.tiktok\.com/[A-Za-z0-9]+',
            r'https?://vm\.tiktok\.com/[A-Za-z0-9]+',
            r'https?://www\.tiktok\.com/@[^/]+/video/\d+'
        ]
        
        for pattern in patterns:
            if re.match(pattern, url):
                return True
        return False
    
    def extract_video_id(self, url: str) -> str:
        """Extract video ID from URL"""
        # For vt.tiktok.com/ABC123
        if 'vt.tiktok.com' in url:
            match = re.search(r'vt\.tiktok\.com/([A-Za-z0-9]+)', url)
            if match:
                return match.group(1)
        
        # For vm.tiktok.com/ABC123
        elif 'vm.tiktok.com' in url:
            match = re.search(r'vm\.tiktok\.com/([A-Za-z0-9]+)', url)
            if match:
                return match.group(1)
        
        # For tiktok.com/@user/video/123456789
        elif 'tiktok.com' in url:
            match = re.search(r'/video/(\d+)', url)
            if match:
                return match.group(1)
        
        return ""
    
    def process_like_request(self, chat_id, message_id, video_id, count):
        """Process like request in background thread"""
        try:
            # Update status
            self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🚀 *Starting...*\n\n🎯 Video ID: `{video_id}`\n📊 Target: `{count}` likes\n\n⏳ Please wait...",
                parse_mode='Markdown'
            )
            
            # Run async task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.core.send_likes(video_id, count))
            loop.close()
            
            # Send result
            if result['status'] in ['success', 'completed']:
                success_msg = f"""
✅ *Likes Sent Successfully!*

🎯 Video ID: `{result['video_id']}`
📤 Requested: `{result['requested_likes']}` likes
✅ Sent: `{result['sent_likes']}` likes
❌ Failed: `{result['failed_likes']}` likes
📈 Success Rate: `{result['success_rate']}`
⏱️ Time Taken: `{result['time_taken']}`
⚡ Speed: `{result['speed']} likes/sec`
🕒 Completed: `{result['timestamp']}`
"""
                self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=success_msg,
                    parse_mode='Markdown'
                )
            else:
                error_msg = f"""
❌ *Failed to Send Likes!*

🎯 Video ID: `{result.get('video_id', 'N/A')}`
📤 Requested: `{result.get('requested_likes', 0)}` likes
✅ Sent: `{result.get('sent_likes', 0)}` likes
❌ Failed: `{result.get('failed_likes', 0)}` likes

💥 Error: `{result.get('message', 'Unknown error')}`
"""
                self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_msg,
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            error_text = f"💥 *Critical Error!*\n\n`{str(e)[:200]}`"
            try:
                self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=error_text,
                    parse_mode='Markdown'
                )
            except:
                self.bot.send_message(chat_id, error_text, parse_mode='Markdown')
    
    def start(self):
        """Start the bot"""
        print("🤖 Telegram Bot starting...")
        try:
            self.bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"❌ Bot error: {e}")
            print("🔄 Restarting in 3 seconds...")
            time.sleep(3)
            self.start()
