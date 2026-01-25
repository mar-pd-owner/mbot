"""
Advanced Telegram Bot with Professional Interface
"""

import telebot
from telebot import types
import asyncio
import threading
import time
from datetime import datetime

class MBotTelegram:
    def __init__(self, token: str, core):
        self.bot = telebot.TeleBot(token)
        self.core = core
        self.user_sessions = {}
        self.setup_handlers()
        
    def setup_handlers(self):
        """Setup all bot commands"""
        
        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            user_id = message.from_user.id
            username = message.from_user.username
            
            welcome_msg = f"""
👑 *Welcome to MBOT {username}!* 👑

🚀 *Ultra-Fast TikTok Like Bot*
⚡ *500+ Likes in Seconds*
🎯 *Short URL Support (vt.tiktok.com)*
✅ *No Captcha Required*
📊 *Real Public Likes*

*📌 Available Commands:*
/like [url] [count] - Send likes to video
/bulk [url1,url2] - Send to multiple videos
/stats - Show bot statistics
/status - Check bot status
/devices - Show active devices
/speed - Test speed
/stop - Stop all tasks

*💡 Examples:*
`/like https://vt.tiktok.com/ZSRLRsxrK/ 500`
`/like https://vm.tiktok.com/ZSRLCgYxv/ 300`
`/bulk url1,url2,url3 200`
            """
            
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton("📖 Tutorial", callback_data="tutorial"),
                types.InlineKeyboardButton("⚡ Speed Test", callback_data="speedtest")
            )
            markup.row(
                types.InlineKeyboardButton("🎯 Send Likes", callback_data="send_likes"),
                types.InlineKeyboardButton("📊 Stats", callback_data="stats")
            )
            
            self.bot.send_message(
                message.chat.id, 
                welcome_msg, 
                parse_mode='Markdown',
                reply_markup=markup
            )
        
        @self.bot.message_handler(commands=['like'])
        def handle_like(message):
            try:
                parts = message.text.split()
                if len(parts) < 2:
                    self.bot.reply_to(message, "❌ Usage: /like [url] [count]\nExample: /like https://vt.tiktok.com/xxx 500")
                    return
                
                url = parts[1]
                count = int(parts[2]) if len(parts) > 2 else 500
                
                # Validate count
                if count > 1000:
                    count = 1000
                
                # Send processing message
                msg = self.bot.reply_to(message, f"⏳ Processing: {url}\n🎯 Target: {count} likes\n\nPlease wait...")
                
                # Run in thread
                thread = threading.Thread(
                    target=self._process_like_request,
                    args=(message.chat.id, msg.message_id, url, count)
                )
                thread.start()
                
            except Exception as e:
                self.bot.reply_to(message, f"❌ Error: {str(e)}")
        
        @self.bot.message_handler(commands=['stats'])
        def handle_stats(message):
            stats = self.core.get_stats()
            stats_msg = f"""
📊 *MBOT Statistics*

✅ Total Likes Sent: `{stats['total_likes_sent']:,}`
🎯 Total Videos: `{stats['total_videos']}`
📈 Success Rate: `{stats['success_rate']:.2f}%`
⚡ Uptime: `{stats['uptime']:.0f}s`
🔧 Active Tasks: `{stats['active_tasks']}`
🕒 Last Activity: `{datetime.fromtimestamp(stats['last_activity']).strftime('%H:%M:%S')}`
            """
            self.bot.send_message(message.chat.id, stats_msg, parse_mode='Markdown')
    
    def _process_like_request(self, chat_id, message_id, url, count):
        """Process like request in background"""
        try:
            # Update status
            self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🚀 *Starting...*\n\nURL: `{url}`\nTarget: `{count}` likes\n\n⏳ Initializing...",
                parse_mode='Markdown'
            )
            
            # Run async task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.core.send_likes(url, count))
            loop.close()
            
            # Send result
            if result['status'] == 'success':
                success_msg = f"""
✅ *Likes Sent Successfully!*

🎯 Video ID: `{result['video_id']}`
📤 Requested: `{result['requested_likes']}` likes
✅ Sent: `{result['sent_likes']}` likes
❌ Failed: `{result['failed_likes']}` likes
📈 Success Rate: `{result['success_rate']}`
⏱️ Time Taken: `{result['time_taken']}`
⚡ Speed: `{result['speed']}`
                """
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🔄 Send More", callback_data=f"more_{url}"))
                
                self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=success_msg,
                    parse_mode='Markdown',
                    reply_markup=markup
                )
            else:
                self.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"❌ *Failed!*\n\nError: {result['message']}",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"❌ *Error!*\n\n{str(e)}",
                parse_mode='Markdown'
            )
    
    def start(self):
        """Start the Telegram bot"""
        print("🤖 Starting Telegram Bot...")
        self.bot.polling(none_stop=True)
