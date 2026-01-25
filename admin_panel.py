"""
MBOT Admin Control Panel
Only accessible by owner
Real-time monitoring and control
"""

import asyncio
import json
import time
import threading
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.types import PeerUser
import sys
import os

class AdminPanel:
    def __init__(self, bot_token, owner_id):
        self.bot_token = bot_token
        self.owner_id = owner_id
        self.client = None
        self.bot_running = True
        self.user_stats = {}
        self.boost_requests = []
        self.active_users = {}
        
        # Load config
        with open('config.json', 'r') as f:
            self.config = json.load(f)
    
    async def start(self):
        """Start admin panel"""
        self.client = TelegramClient(
            'admin_panel_session',
            api_id=2040,
            api_hash='b18441a1ff607e10a989891a5462e627'
        ).start(bot_token=self.bot_token)
        
        print("🛡️ Admin Panel Started")
        
        # Setup admin handlers
        @self.client.on(events.NewMessage(from_users=[self.owner_id]))
        async def admin_handler(event):
            """Handle admin commands"""
            text = event.text
            
            if text == '/admin':
                await self.show_admin_panel(event)
            elif text == '/users':
                await self.show_users(event)
            elif text == '/stats':
                await self.show_system_stats(event)
            elif text == '/broadcast':
                await self.broadcast_menu(event)
            elif text.startswith('/ban'):
                await self.ban_user(event)
            elif text.startswith('/unban'):
                await self.unban_user(event)
            elif text.startswith('/reply'):
                await self.reply_to_user(event)
            elif text == '/restart':
                await self.restart_bot(event)
            elif text == '/stop':
                await self.stop_bot(event)
            elif text == '/logs':
                await self.send_logs(event)
            elif text == '/devices':
                await self.show_devices(event)
            elif text == '/version':
                await self.show_real_version(event)
            elif text == '/help':
                await self.admin_help(event)
        
        # Run until disconnected
        await self.client.run_until_disconnected()
    
    async def show_admin_panel(self, event):
        """Show admin panel"""
        panel = f"""
👑 **MBOT ADMIN PANEL** (v{self.config['version']})

📊 **System Status:** {'🟢 RUNNING' if self.bot_running else '🔴 STOPPED'}
👥 **Total Users:** {len(self.user_stats)}
🚀 **Active Boosts:** {len(self.boost_requests)}
🔄 **Real Version:** 75 (Hidden)

📋 **Admin Commands:**
`/users` - View all users
`/stats` - System statistics
`/broadcast` - Broadcast message
`/reply <user_id> <msg>` - Reply to user
`/ban <user_id>` - Ban user
`/unban <user_id>` - Unban user
`/devices` - Device manager
`/logs` - View logs
`/restart` - Restart bot
`/stop` - Stop bot
`/version` - Show real version

🔒 **Owner:** @{self.config['owner_username']}
"""
        
        buttons = [
            [Button.inline("👥 Users", b"admin_users"),
             Button.inline("📊 Stats", b"admin_stats")],
            [Button.inline("📢 Broadcast", b"admin_broadcast"),
             Button.inline("⚙️ Devices", b"admin_devices")],
            [Button.inline("🔄 Restart", b"admin_restart"),
             Button.inline("⏹️ Stop", b"admin_stop")]
        ]
        
        await event.respond(panel, buttons=buttons)
    
    async def show_users(self, event):
        """Show all users"""
        try:
            with open('user_data.json', 'r') as f:
                users = json.load(f)
        except:
            users = {}
        
        if not users:
            await event.respond("📭 No users yet")
            return
        
        user_list = "👥 **All Users:**\n\n"
        for user_id, data in list(users.items())[:50]:  # Show first 50
            username = data.get('username', 'N/A')
            boosts = data.get('total_boosts', 0)
            user_list += f"• `{user_id}` - @{username} (Boosts: {boosts})\n"
        
        if len(users) > 50:
            user_list += f"\n... and {len(users) - 50} more users"
        
        await event.respond(user_list)
    
    async def show_system_stats(self, event):
        """Show system statistics"""
        try:
            # Read log file
            with open('mbot.log', 'r') as f:
                logs = f.readlines()
            
            # Count activities
            boosts = sum(1 for line in logs if 'boosted_video' in line)
            likes = sum(1 for line in logs if 'liked_video' in line)
            errors = sum(1 for line in logs if 'ERROR' in line)
            
            stats = f"""
📈 **SYSTEM STATISTICS**

📊 **Performance:**
• Total Boosts: {boosts}
• Total Likes: {likes}
• Total Errors: {errors}
• Uptime: {self.get_uptime()}

👥 **User Stats:**
• Total Users: {len(self.user_stats)}
• Active Today: {self.get_active_today()}
• Banned Users: {self.get_banned_count()}

⚙️ **System Info:**
• Bot Version: v{self.config['version']}
• Real Version: v75
• Max Threads: {self.config['max_threads']}
• Boost Speed: {self.config['boost_speed']}
• Proxy Enabled: {self.config['proxy_enabled']}

💾 **Storage:**
• Log Size: {len(logs)} lines
• User Data: {len(self.user_stats)} records
"""
            
            await event.respond(stats)
            
        except Exception as e:
            await event.respond(f"❌ Error: {e}")
    
    async def broadcast_menu(self, event):
        """Broadcast message to all users"""
        await event.respond("📢 **Broadcast Message**\n\nSend your message to broadcast to all users:")
        
        @self.client.on(events.NewMessage(from_users=[self.owner_id]))
        async def wait_for_message(broadcast_event):
            if broadcast_event.text and not broadcast_event.text.startswith('/'):
                message = broadcast_event.text
                await self.send_broadcast(event, message)
    
    async def send_broadcast(self, event, message):
        """Send broadcast to all users"""
        try:
            with open('user_data.json', 'r') as f:
                users = json.load(f)
            
            sent = 0
            failed = 0
            
            for user_id in users.keys():
                try:
                    await self.client.send_message(
                        int(user_id),
                        f"📢 **Broadcast from MBOT:**\n\n{message}\n\n⚠️ *This is an automated message*"
                    )
                    sent += 1
                    await asyncio.sleep(0.1)  # Rate limiting
                except:
                    failed += 1
            
            await event.respond(f"✅ Broadcast sent!\n\nSuccess: {sent}\nFailed: {failed}")
            
        except Exception as e:
            await event.respond(f"❌ Broadcast failed: {e}")
    
    async def ban_user(self, event):
        """Ban a user"""
        try:
            args = event.text.split()
            if len(args) < 2:
                await event.respond("❌ Usage: `/ban <user_id>`")
                return
            
            user_id = args[1]
            
            # Load banned users
            try:
                with open('banned_users.json', 'r') as f:
                    banned = json.load(f)
            except:
                banned = []
            
            if user_id not in banned:
                banned.append(user_id)
                with open('banned_users.json', 'w') as f:
                    json.dump(banned, f)
                
                await event.respond(f"✅ User `{user_id}` has been banned")
            else:
                await event.respond(f"⚠️ User `{user_id}` is already banned")
                
        except Exception as e:
            await event.respond(f"❌ Error: {e}")
    
    async def reply_to_user(self, event):
        """Reply to a specific user"""
        try:
            args = event.text.split(maxsplit=2)
            if len(args) < 3:
                await event.respond("❌ Usage: `/reply <user_id> <message>`")
                return
            
            user_id = args[1]
            message = args[2]
            
            # Send reply
            await self.client.send_message(
                int(user_id),
                f"📨 **Admin Reply:**\n\n{message}\n\n⚠️ *This is an automated reply from MBOT*"
            )
            
            await event.respond(f"✅ Reply sent to user `{user_id}`")
            
        except Exception as e:
            await event.respond(f"❌ Error: {e}")
    
    async def send_logs(self, event):
        """Send log file"""
        try:
            with open('mbot.log', 'r') as f:
                logs = f.readlines()[-100:]  # Last 100 lines
            
            log_text = "".join(logs)
            
            if len(log_text) > 4000:
                # Split if too long
                chunks = [log_text[i:i+4000] for i in range(0, len(log_text), 4000)]
                for chunk in chunks:
                    await event.respond(f"```\n{chunk}\n```", parse_mode='markdown')
            else:
                await event.respond(f"```\n{log_text}\n```", parse_mode='markdown')
                
        except Exception as e:
            await event.respond(f"❌ Error: {e}")
    
    async def show_devices(self, event):
        """Show device information"""
        try:
            with open('devices.txt', 'r') as f:
                devices = f.readlines()
            
            device_count = len(devices)
            device_info = f"""
📱 **DEVICE MANAGER**

Total Devices: {device_count}

**Sample Devices:**
"""
            for i, device in enumerate(devices[:5], 1):
                parts = device.strip().split(':')
                if len(parts) >= 4:
                    device_info += f"{i}. DID: {parts[0][:8]}...\n"
            
            if device_count > 5:
                device_info += f"\n... and {device_count - 5} more devices"
            
            buttons = [
                [Button.inline("🔄 Refresh", b"refresh_devices"),
                 Button.inline("➕ Add", b"add_device")],
                [Button.inline("🗑️ Remove", b"remove_device")]
            ]
            
            await event.respond(device_info, buttons=buttons)
            
        except Exception as e:
            await event.respond(f"❌ Error: {e}")
    
    async def show_real_version(self, event):
        """Show real version information"""
        version_info = f"""
🔐 **REAL VERSION INFORMATION**

**Public Version:** v{self.config['version']}
**Real Version:** v75

**Hidden Features:**
1. Advanced anti-detection system
2. Multi-layer encryption
3. Auto-IP rotation
4. Device fingerprint spoofing
5. Request randomization
6. Traffic obfuscation
7. Proxy chaining support
8. Auto-ban evasion
9. Session persistence
10. Real-time analytics

**Security Layers:** 7
**Encryption Level:** Military Grade
**Anonymity:** 100%

⚠️ **This information is for owner only**
"""
        
        await event.respond(version_info)
    
    async def admin_help(self, event):
        """Show admin help"""
        help_text = """
🛡️ **ADMIN COMMANDS GUIDE**

**User Management:**
`/users` - View all users
`/ban <user_id>` - Ban a user
`/unban <user_id>` - Unban a user
`/reply <user_id> <msg>` - Reply to user

**System Control:**
`/stats` - System statistics
`/broadcast` - Broadcast to all users
`/restart` - Restart the bot
`/stop` - Stop the bot
`/logs` - View system logs

**Configuration:**
`/devices` - Manage devices
`/version` - Show real version

**Monitoring:**
• All user activities are logged
• Real-time boost monitoring
• Error tracking and reporting
• Performance analytics

🔒 **Owner Access Only**
"""
        
        await event.respond(help_text)
    
    def get_uptime(self):
        """Get bot uptime"""
        # This would read from a file where start time is stored
        try:
            with open('start_time.txt', 'r') as f:
                start_time = float(f.read())
            uptime = time.time() - start_time
            
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            seconds = int(uptime % 60)
            
            return f"{hours}h {minutes}m {seconds}s"
        except:
            return "Unknown"
    
    def get_active_today(self):
        """Get active users today"""
        try:
            with open('user_data.json', 'r') as f:
                users = json.load(f)
            
            today = datetime.now().strftime("%Y-%m-%d")
            active = 0
            
            for user_data in users.values():
                if user_data.get('last_active', '').startswith(today):
                    active += 1
            
            return active
        except:
            return 0
    
    def get_banned_count(self):
        """Get number of banned users"""
        try:
            with open('banned_users.json', 'r') as f:
                banned = json.load(f)
            return len(banned)
        except:
            return 0
    
    async def restart_bot(self, event):
        """Restart the bot"""
        await event.respond("🔄 Restarting MBOT...")
        os.execv(sys.executable, ['python'] + sys.argv)
    
    async def stop_bot(self, event):
        """Stop the bot"""
        self.bot_running = False
        await event.respond("⏹️ MBOT stopped. Use `/start` to restart.")
        sys.exit(0)

def main():
    """Start admin panel"""
    print("""
🛡️ MBOT Admin Panel
Version: 1.0 (Real: 75)
Owner: @rana_editz_00
    """)
    
    # Load config
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    panel = AdminPanel(
        bot_token=config['bot_token'],
        owner_id=config['owner_id']
    )
    
    asyncio.run(panel.start())

if __name__ == "__main__":
    main()
