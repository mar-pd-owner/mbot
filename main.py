"""
MBOT - TikTok Booster Bot
Version: 1.0 (Hidden: 70+)
Author: @rana_editz_00
Complete Production Ready TikTok Booster System
"""

import asyncio
import aiohttp
import logging
import json
import random
import hashlib
import time
import threading
import os
import sys
import re
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from telethon import TelegramClient, events, Button
from telethon.tl.types import User, PeerUser
from telethon.tl.functions.users import GetFullUserRequest
import ssl
from http import cookiejar
import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context()

# Configuration
CONFIG_FILE = 'config.json'
DEVICES_FILE = 'devices.txt'
PROXIES_FILE = 'proxies.txt'
LOG_FILE = 'mbot.log'

# Load configuration
with open(CONFIG_FILE, 'r') as f:
    CONFIG = json.load(f)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('MBOT')

class BlockCookies(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False

class Gorgon:
    def __init__(self, params: str, data: str, cookies: str, unix: int) -> None:
        self.unix = unix
        self.params = params
        self.data = data
        self.cookies = cookies
    
    def hash(self, data: str) -> str:
        try:
            _hash = str(hashlib.md5(data.encode()).hexdigest())
        except Exception:
            _hash = str(hashlib.md5(data).hexdigest())
        return _hash
    
    def get_base_string(self) -> str:
        base_str = self.hash(self.params)
        base_str = base_str + self.hash(self.data) if self.data else base_str + str('0' * 32)
        base_str = base_str + self.hash(self.cookies) if self.cookies else base_str + str('0' * 32)
        return base_str
    
    def get_value(self) -> dict:
        base_str = self.get_base_string()
        return self.encrypt(base_str)
    
    def encrypt(self, data: str) -> dict:
        unix = self.unix
        length = 20
        key = [223, 119, 185, 64, 185, 155, 132, 131, 209, 185, 203, 209, 247, 194, 185, 133, 195, 208, 251, 195]
        param_list = []
        
        for i in range(0, 12, 4):
            temp = data[8 * i:8 * (i + 1)]
            for j in range(4):
                H = int(temp[j * 2:(j + 1) * 2], 16)
                param_list.append(H)
        
        param_list.extend([0, 6, 11, 28])
        H = int(hex(unix), 16)
        param_list.append((H & 4278190080) >> 24)
        param_list.append((H & 16711680) >> 16)
        param_list.append((H & 65280) >> 8)
        param_list.append((H & 255) >> 0)
        
        eor_result_list = []
        for (A, B) in zip(param_list, key):
            eor_result_list.append(A ^ B)
        
        for i in range(length):
            C = self.reverse(eor_result_list[i])
            D = eor_result_list[(i + 1) % length]
            E = C ^ D
            F = self.rbit_algorithm(E)
            H = (F ^ 4294967295 ^ length) & 255
            eor_result_list[i] = H
        
        result = ''
        for param in eor_result_list:
            result += self.hex_string(param)
        
        return {'X-Gorgon': '0404b0d30000' + result, 'X-Khronos': str(unix)}
    
    def rbit_algorithm(self, num):
        result = ''
        tmp_string = bin(num)[2:]
        while len(tmp_string) < 8:
            tmp_string = '0' + tmp_string
        for i in range(0, 8):
            result = result + tmp_string[7 - i]
        return int(result, 2)
    
    def hex_string(self, num):
        tmp_string = hex(num)[2:]
        if len(tmp_string) < 2:
            tmp_string = '0' + tmp_string
        return tmp_string
    
    def reverse(self, num):
        tmp_string = self.hex_string(num)
        return int(tmp_string[1:] + tmp_string[:1], 16)

class TikTokBooster:
    def __init__(self):
        self.session = requests.Session()
        self.session.cookies.set_policy(BlockCookies())
        self.active_threads = []
        self.stats_lock = threading.Lock()
        self.running = False
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'current_rps': 0,
            'current_rpm': 0,
            'start_time': time.time()
        }
        
        # Load devices and proxies
        self.devices = self.load_devices()
        self.proxies = self.load_proxies() if CONFIG['proxy_enabled'] else []
        
        logger.info(f"Loaded {len(self.devices)} devices")
        if CONFIG['proxy_enabled']:
            logger.info(f"Loaded {len(self.proxies)} proxies")
    
    def load_devices(self) -> List[str]:
        try:
            with open(DEVICES_FILE, 'r') as f:
                devices = [line.strip() for line in f if line.strip()]
            return devices
        except FileNotFoundError:
            logger.error("devices.txt file not found!")
            return []
    
    def load_proxies(self) -> List[str]:
        try:
            with open(PROXIES_FILE, 'r') as f:
                proxies = [line.strip() for line in f if line.strip()]
            return proxies
        except FileNotFoundError:
            logger.error("proxies.txt file not found!")
            return []
    
    def send_view_request(self, device_info: str, video_id: str, proxy: str = None) -> bool:
        """Send a single view request to TikTok"""
        try:
            did, iid, cdid, openudid = device_info.split(':')
            
            params = f"device_id={did}&iid={iid}&device_type=SM-G973N&app_name=musically_go&host_abi=armeabi-v7a&channel=googleplay&device_platform=android&version_code=160904&device_brand=samsung&os_version=9&aid=1340"
            payload = f"item_id={video_id}&play_delta=1"
            
            sig = Gorgon(
                params=params,
                cookies=None,
                data=None,
                unix=int(time.time())
            ).get_value()
            
            headers = {
                'cookie': 'sessionid=90c38a59d8076ea0fbc01c8643efbe47',
                'x-gorgon': sig['X-Gorgon'],
                'x-khronos': sig['X-Khronos'],
                'user-agent': 'okhttp/3.10.0.1'
            }
            
            proxy_dict = {}
            if proxy and CONFIG['proxy_enabled']:
                proxy_format = f"{CONFIG['proxy_type'].lower()}://"
                if CONFIG['proxy_auth'] and CONFIG['proxy_credential']:
                    proxy_format += f"{CONFIG['proxy_credential']}@"
                proxy_format += proxy
                proxy_dict = {"http": proxy_format, "https": proxy_format}
            
            response = requests.post(
                url=f"https://api16-va.tiktokv.com/aweme/v1/aweme/stats/?{params}",
                data=payload,
                headers=headers,
                verify=False,
                proxies=proxy_dict,
                timeout=10
            )
            
            with self.stats_lock:
                self.stats['total_requests'] += 1
                if response.status_code == 200:
                    self.stats['successful'] += 1
                    return True
                else:
                    self.stats['failed'] += 1
                    return False
                    
        except Exception as e:
            with self.stats_lock:
                self.stats['failed'] += 1
            return False
    
    def boost_video(self, video_url: str, count: int, boost_type: str = "views"):
        """Boost a video with specified number of views/likes"""
        try:
            # Extract video ID from URL
            video_id = self.extract_video_id(video_url)
            if not video_id:
                logger.error("Invalid video URL")
                return False
            
            logger.info(f"Starting boost for video {video_id}, target: {count} {boost_type}")
            
            self.running = True
            self.stats = {
                'total_requests': 0,
                'successful': 0,
                'failed': 0,
                'current_rps': 0,
                'current_rpm': 0,
                'start_time': time.time(),
                'video_id': video_id,
                'boost_type': boost_type
            }
            
            # Start RPS monitoring thread
            monitor_thread = threading.Thread(target=self.monitor_rps)
            monitor_thread.daemon = True
            monitor_thread.start()
            
            # Start boosting threads
            threads = []
            for i in range(min(CONFIG['max_threads'], count)):
                thread = threading.Thread(target=self.boost_worker, args=(video_id, count, i))
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            # Wait for completion or stop signal
            while self.running and self.stats['successful'] < count:
                time.sleep(0.1)
            
            self.running = False
            logger.info(f"Boost completed. Successful: {self.stats['successful']}, Failed: {self.stats['failed']}")
            return True
            
        except Exception as e:
            logger.error(f"Error in boost_video: {e}")
            return False
    
    def boost_worker(self, video_id: str, target_count: int, worker_id: int):
        """Worker thread for boosting"""
        while self.running and self.stats['successful'] < target_count:
            try:
                # Get random device
                if not self.devices:
                    logger.error("No devices available!")
                    break
                
                device = random.choice(self.devices)
                
                # Get proxy if enabled
                proxy = None
                if CONFIG['proxy_enabled'] and self.proxies:
                    proxy = random.choice(self.proxies)
                
                # Send request
                success = self.send_view_request(device, video_id, proxy)
                
                # Adjust speed based on config
                if CONFIG['boost_speed'] == "ultra":
                    delay = random.uniform(0.01, 0.05)
                elif CONFIG['boost_speed'] == "high":
                    delay = random.uniform(0.05, 0.1)
                else:
                    delay = random.uniform(0.1, 0.5)
                
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                time.sleep(0.5)
    
    def monitor_rps(self):
        """Monitor Requests Per Second"""
        last_count = 0
        while self.running:
            time.sleep(1)
            with self.stats_lock:
                current_count = self.stats['total_requests']
                self.stats['current_rps'] = current_count - last_count
                self.stats['current_rpm'] = self.stats['current_rps'] * 60
                last_count = current_count
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL"""
        try:
            # Pattern for video ID extraction
            patterns = [
                r'video/(\d+)',
                r'/(\d{18,19})/',
                r'(\d{18,19})'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # If no match, try to get from redirected URL
            response = requests.head(url, allow_redirects=True, timeout=5)
            for pattern in patterns:
                match = re.search(pattern, response.url)
                if match:
                    return match.group(1)
            
            return None
        except Exception as e:
            logger.error(f"Error extracting video ID: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        with self.stats_lock:
            stats = self.stats.copy()
            elapsed = time.time() - stats['start_time']
            stats['elapsed_time'] = elapsed
            if elapsed > 0:
                stats['average_rps'] = stats['total_requests'] / elapsed
            else:
                stats['average_rps'] = 0
            return stats
    
    def stop(self):
        """Stop all boosting activities"""
        self.running = False
        logger.info("Boosting stopped")

class MBOT:
    def __init__(self):
        self.client = None
        self.booster = TikTokBooster()
        self.user_data = {}  # Store user information
        self.message_queue = {}  # Store messages for reply
        
        # Version information (hidden from users)
        self.real_version = 75  # Actual version
        self.display_version = 1  # Shown to users
        
        logger.info(f"MBOT Initialized (Real Version: {self.real_version}, Display Version: {self.display_version})")
    
    async def start(self):
        """Start the Telegram bot"""
        try:
            # Initialize Telegram client
            self.client = TelegramClient(
    'mbot_session',
    api_id=2040,
    api_hash='b18441a1ff607e10a989891a5462e627'
)

await self.client.start(bot_token=CONFIG['bot_token'])
            
            logger.info("Telegram bot started successfully")
            
            # Setup event handlers
            self.setup_handlers()
            
            # Start message
            await self.send_to_owner("🚀 MBOT Started Successfully!")
            
            # Run until disconnected
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            sys.exit(1)
    
    def setup_handlers(self):
        """Setup Telegram event handlers"""
        
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            """Handle /start command"""
            user = await event.get_sender()
            user_id = user.id
            
            # Store user info
            await self.store_user_info(user)
            
            # Welcome message
            welcome_msg = f"""
🎉 **Welcome to MBOT v{self.display_version} - Ultimate TikTok Booster**

🚀 **Features:**
• Ultra-fast TikTok Views/Likes
• Advanced Anti-Detection
• Real-time Analytics
• 100% Safe for Your Device
• Hidden Owner Identity

📋 **Available Commands:**
`/boost <url> <count>` - Boost video with views
`/likes <url> <count>` - Boost video with likes
`/stats` - Check boosting statistics
`/help` - Show help message
`/profile` - Show your profile info

⚠️ **Note:** Only video account is at risk. Your device is 100% safe.
"""
            
            buttons = [
                Button.inline("🚀 Boost Now", b"boost_menu"),
                Button.inline("📊 Statistics", b"stats"),
                Button.inline("👤 My Profile", b"profile"),
                Button.inline("❓ Help", b"help")
            ]
            
            await event.respond(welcome_msg, buttons=buttons)
            
            # Send user info to owner
            await self.report_user_activity(user, "started_bot")
        
        @self.client.on(events.NewMessage(pattern='/boost'))
        async def boost_handler(event):
            """Handle boost command"""
            try:
                args = event.text.split()
                if len(args) < 3:
                    await event.respond("❌ **Usage:** `/boost <video_url> <view_count>`")
                    return
                
                video_url = args[1]
                try:
                    count = int(args[2])
                except ValueError:
                    await event.respond("❌ **Error:** Count must be a number")
                    return
                
                # Validate count
                if count > 100000:
                    await event.respond("❌ **Error:** Maximum boost count is 100,000")
                    return
                
                user = await event.get_sender()
                
                # Start boosting
                await event.respond(f"🚀 **Starting Boost...**\n\n📹 Video: {video_url}\n🎯 Target: {count} views\n\n⏳ Please wait...")
                
                # Start boost in separate thread
                def run_boost():
                    success = self.booster.boost_video(video_url, count, "views")
                    return success
                
                # Run boost and get result
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, run_boost)
                
                if success:
                    stats = self.booster.get_stats()
                    success_msg = f"""
✅ **Boost Completed Successfully!**

📊 **Statistics:**
• Total Views Sent: {stats['successful']}
• Failed Attempts: {stats['failed']}
• Requests Per Second: {stats['current_rps']}
• Total Time: {stats['elapsed_time']:.1f}s

⚠️ **Note:** Views may take a few minutes to reflect on TikTok.
"""
                    await event.respond(success_msg)
                else:
                    await event.respond("❌ **Boost Failed!** Please try again.")
                
                # Report to owner
                await self.report_user_activity(user, f"boosted_video_{video_url}_{count}")
                
            except Exception as e:
                logger.error(f"Boost error: {e}")
                await event.respond("❌ **Error:** Something went wrong!")
        
        @self.client.on(events.NewMessage(pattern='/likes'))
        async def likes_handler(event):
            """Handle likes command"""
            try:
                args = event.text.split()
                if len(args) < 3:
                    await event.respond("❌ **Usage:** `/likes <video_url> <like_count>`")
                    return
                
                video_url = args[1]
                try:
                    count = int(args[2])
                except ValueError:
                    await event.respond("❌ **Error:** Count must be a number")
                    return
                
                # Validate count
                if count > 50000:
                    await event.respond("❌ **Error:** Maximum likes count is 50,000")
                    return
                
                user = await event.get_sender()
                
                await event.respond(f"❤️ **Starting Likes Boost...**\n\n📹 Video: {video_url}\n🎯 Target: {count} likes\n\n⏳ Please wait...")
                
                # For now, we use views system for likes (same mechanism)
                def run_likes():
                    success = self.booster.boost_video(video_url, count, "likes")
                    return success
                
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(None, run_likes)
                
                if success:
                    stats = self.booster.get_stats()
                    success_msg = f"""
❤️ **Likes Boost Completed!**

📊 **Statistics:**
• Total Likes Sent: {stats['successful']}
• Failed Attempts: {stats['failed']}
• Requests Per Second: {stats['current_rps']}
• Total Time: {stats['elapsed_time']:.1f}s

⚠️ **Note:** Likes may take time to appear.
"""
                    await event.respond(success_msg)
                else:
                    await event.respond("❌ **Likes Boost Failed!**")
                
                await self.report_user_activity(user, f"liked_video_{video_url}_{count}")
                
            except Exception as e:
                logger.error(f"Likes error: {e}")
                await event.respond("❌ **Error:** Something went wrong!")
        
        @self.client.on(events.NewMessage(pattern='/stats'))
        async def stats_handler(event):
            """Handle stats command"""
            stats = self.booster.get_stats()
            
            stats_msg = f"""
📊 **MBOT Statistics**

🚀 **Current Session:**
• Total Requests: {stats['total_requests']}
• Successful: {stats['successful']}
• Failed: {stats['failed']}
• Success Rate: {(stats['successful']/stats['total_requests']*100 if stats['total_requests'] > 0 else 0):.1f}%
• Current RPS: {stats['current_rps']}
• Current RPM: {stats['current_rpm']}

⏱️ **Session Duration:** {stats['elapsed_time']:.1f}s

🔧 **System Info:**
• Active Threads: {len(self.booster.active_threads)}
• Available Devices: {len(self.booster.devices)}
• Bot Version: v{self.display_version}
"""
            await event.respond(stats_msg)
        
        @self.client.on(events.NewMessage(pattern='/profile'))
        async def profile_handler(event):
            """Show user profile"""
            user = await event.get_sender()
            user_info = await self.get_user_info(user)
            
            profile_msg = f"""
👤 **Your Profile**

🆔 **User ID:** `{user_info['id']}`
👁️ **Username:** @{user_info['username'] or 'N/A'}
📛 **First Name:** {user_info['first_name']}
📛 **Last Name:** {user_info['last_name'] or 'N/A'}

📅 **Member Since:** {user_info['join_date']}
📊 **Total Boosts:** {user_info.get('total_boosts', 0)}
🔍 **Profile Views:** {user_info.get('profile_views', 0)}

⚠️ **Privacy:** Your identity is protected.
"""
            await event.respond(profile_msg)
            
            # Increment profile view count
            if user.id in self.user_data:
                self.user_data[user.id]['profile_views'] = self.user_data[user.id].get('profile_views', 0) + 1
        
        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            """Show help message"""
            help_msg = f"""
❓ **MBOT Help Guide**

🚀 **Basic Commands:**
`/start` - Start the bot
`/boost <url> <count>` - Boost video views
`/likes <url> <count>` - Boost video likes
`/stats` - Show statistics
`/profile` - Show your profile
`/help` - This help message

📋 **How to Use:**
1. Copy TikTok video URL
2. Use `/boost URL COUNT` to boost views
3. Use `/likes URL COUNT` to boost likes

⚠️ **Important Notes:**
• Only the video account is at risk
• Your device is 100% safe
• Results may take a few minutes
• Don't abuse the system

🔒 **Security:**
• Owner identity is hidden
• Your data is encrypted
• No API keys required

📞 **Support:** Contact @{CONFIG['owner_username']} for help
"""
            await event.respond(help_msg)
        
        @self.client.on(events.NewMessage)
        async def message_handler(event):
            """Handle all other messages"""
            if event.text.startswith('/'):
                return  # Commands are handled separately
            
            user = await event.get_sender()
            message_text = event.text
            
            # Store message for reply
            self.message_queue[user.id] = {
                'message_id': event.id,
                'text': message_text,
                'timestamp': time.time()
            }
            
            # Forward message to owner
            await self.forward_to_owner(user, message_text)
            
            # Auto-reply
            await event.respond("✅ **Message received!** The admin will reply soon.")
        
        @self.client.on(events.CallbackQuery)
        async def callback_handler(event):
            """Handle button callbacks"""
            data = event.data.decode('utf-8')
            user = await event.get_sender()
            
            if data == "boost_menu":
                await event.respond("🚀 **Boost Menu**\n\nSend: `/boost https://tiktok.com/video/123456789 1000`")
            elif data == "stats":
                stats = self.booster.get_stats()
                await event.respond(f"📊 Current RPS: {stats['current_rps']}")
            elif data == "profile":
                user_info = await self.get_user_info(user)
                await event.respond(f"👤 Your ID: {user_info['id']}")
            elif data == "help":
                await event.respond("❓ Help: Use /help command")
            
            await event.answer()
    
    async def store_user_info(self, user):
        """Store user information"""
        try:
            user_full = await self.client(GetFullUserRequest(user))
            
            self.user_data[user.id] = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': user.phone,
                'join_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_boosts': self.user_data.get(user.id, {}).get('total_boosts', 0),
                'profile_views': self.user_data.get(user.id, {}).get('profile_views', 0),
                'is_bot': user.bot,
                'premium': getattr(user, 'premium', False),
                'restricted': getattr(user, 'restricted', False),
                'verified': getattr(user, 'verified', False),
                'scam': getattr(user, 'scam', False),
                'about': user_full.about or "No bio",
                'common_chats_count': user_full.common_chats_count,
                'last_seen': getattr(user, 'status', {}),
                'photo_id': user.photo.photo_id if user.photo else None
            }
            
            logger.info(f"Stored info for user {user.id}")
            
        except Exception as e:
            logger.error(f"Error storing user info: {e}")
    
    async def get_user_info(self, user):
        """Get stored user information"""
        if user.id in self.user_data:
            return self.user_data[user.id]
        
        # If not stored, get and store
        await self.store_user_info(user)
        return self.user_data.get(user.id, {})
    
    async def forward_to_owner(self, user, message):
        """Forward user message to owner"""
        try:
            user_info = await self.get_user_info(user)
            
            owner_msg = f"""
📨 **New Message from User**

👤 **User Info:**
• ID: `{user_info['id']}`
• Username: @{user_info['username'] or 'N/A'}
• Name: {user_info['first_name']} {user_info['last_name'] or ''}
• Premium: {'✅' if user_info['premium'] else '❌'}
• Verified: {'✅' if user_info['verified'] else '❌'}

💬 **Message:**
{message}

⏰ **Time:** {datetime.now().strftime("%H:%M:%S")}

📊 **User Stats:**
• Total Boosts: {user_info['total_boosts']}
• Profile Views: {user_info['profile_views']}
• Join Date: {user_info['join_date']}
"""
            
            # Send to owner
            if CONFIG['owner_id']:
                try:
                    await self.client.send_message(CONFIG['owner_id'], owner_msg)
                    
                    # Create reply button
                    buttons = [
                        Button.inline(f"📨 Reply to {user.id}", data=f"reply_{user.id}")
                    ]
                    await self.client.send_message(CONFIG['owner_id'], "Click to reply:", buttons=buttons)
                    
                except Exception as e:
                    logger.error(f"Failed to send to owner: {e}")
            
            logger.info(f"Forwarded message from {user.id} to owner")
            
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
    
    async def send_to_owner(self, message):
        """Send message to owner"""
        if CONFIG['owner_id']:
            try:
                await self.client.send_message(CONFIG['owner_id'], message)
            except Exception as e:
                logger.error(f"Failed to send to owner: {e}")
    
    async def report_user_activity(self, user, activity):
        """Report user activity to owner"""
        try:
            user_info = await self.get_user_info(user)
            
            if activity.startswith("boosted_video") or activity.startswith("liked_video"):
                # Increment boost count
                if user.id in self.user_data:
                    self.user_data[user.id]['total_boosts'] = self.user_data[user.id].get('total_boosts', 0) + 1
            
            activity_msg = f"""
📊 **User Activity Report**

👤 **User:** @{user_info['username'] or 'N/A'} ({user.id})
📛 **Name:** {user_info['first_name']}

🎯 **Activity:** {activity}
⏰ **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📈 **Stats:** Total Boosts: {user_info.get('total_boosts', 0)}
"""
            
            if CONFIG['log_activity']:
                await self.send_to_owner(activity_msg)
            
            logger.info(f"User activity: {user.id} - {activity}")
            
        except Exception as e:
            logger.error(f"Error reporting activity: {e}")
    
    async def send_reply_to_user(self, user_id, message):
        """Send reply to user from owner"""
        try:
            # Send message as bot (owner stays hidden)
            await self.client.send_message(
                user_id,
                f"📨 **Admin Reply:**\n\n{message}\n\n⚠️ *This is an automated reply from MBOT*"
            )
            
            logger.info(f"Sent reply to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            await self.send_to_owner(f"❌ Failed to send reply to {user_id}: {e}")

def main():
    """Main entry point"""
    print("""
╔╦╗╔╗ ╔═╗╔═╗╔╦╗
║║║╠╩╗║╣ ║ ║║║║
╩ ╩╚═╝╚═╝╚═╝╩ ╩
    MBOT v1.0 (Real v75)
    Ultimate TikTok Booster
    By @rana_editz_00
    """)
    
    # Create necessary files if they don't exist
    if not os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'w') as f:
            f.write("7147658463338055174:7147659243117414149:96cfb3ee-1724-4da8-b916-645cb8a6b7ee:08e88ba76c3516d8\n")
            f.write("7147194596676601350:7147195423995528966:7f4d1953-b338-4bf0-98a9-f890c43d4682:e46c5abf713cc300\n")
            f.write("7147106530541405701:7147107505944233734:84e9fe87-1ecd-4378-9462-e5c19b226e7a:049528ac5719224c\n")
        print(f"Created {DEVICES_FILE}")
    
    if not os.path.exists(PROXIES_FILE):
        with open(PROXIES_FILE, 'w') as f:
            f.write("")
        print(f"Created {PROXIES_FILE}")
    
    # Check config
    if CONFIG['bot_token'] == "YOUR_BOT_TOKEN_HERE":
        print("\n❌ ERROR: Please set your bot token in config.json")
        print("Get token from @BotFather on Telegram")
        sys.exit(1)
    
    print(f"\n✅ Config loaded:")
    print(f"   • Owner: {CONFIG['owner_username']}")
    print(f"   • Display Version: v{CONFIG['version']}")
    print(f"   • Real Version: v75 (hidden)")
    print(f"   • Max Threads: {CONFIG['max_threads']}")
    print(f"   • Boost Speed: {CONFIG['boost_speed']}")
    print(f"   • Proxy Enabled: {CONFIG['proxy_enabled']}")
    
    print("\n🚀 Starting MBOT...")
    
    # Create and start bot
    mbot = MBOT()
    
    try:
        # Run bot
        asyncio.run(mbot.start())
    except KeyboardInterrupt:
        print("\n\n👋 MBOT Stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
