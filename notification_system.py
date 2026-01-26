"""
Advanced Notification System for MBOT
Sends notifications to users and admin via multiple channels
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta
import threading
from telethon import TelegramClient
from telethon.tl.types import PeerUser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

class NotificationSystem:
    def __init__(self, bot_token: str = None, owner_id: int = None):
        self.bot_token = bot_token
        self.owner_id = owner_id
        self.telegram_client = None
        self.notification_queue = []
        self.queue_lock = threading.Lock()
        self.notification_config = self.load_config()
        self.running = True
        
        # Start notification worker
        self.worker_thread = threading.Thread(target=self.process_notifications)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        
        # Initialize Telegram client if token provided
        if bot_token:
            self.init_telegram_client()
    
    def load_config(self) -> Dict:
        """Load notification configuration"""
        try:
            with open('notification_config.json', 'r') as f:
                return json.load(f)
        except:
            return {
                "telegram_enabled": True,
                "email_enabled": False,
                "webhook_enabled": False,
                "notification_types": {
                    "boost_completed": True,
                    "boost_failed": True,
                    "new_user": True,
                    "security_alert": True,
                    "system_alert": True,
                    "promotional": False
                },
                "rate_limits": {
                    "user": 5,  # per hour
                    "admin": 100  # per hour
                }
            }
    
    def init_telegram_client(self):
        """Initialize Telegram client"""
        try:
            self.telegram_client = TelegramClient(
                'notification_session',
                api_id=2040,
                api_hash='b18441a1ff607e10a989891a5462e627'
            ).start(bot_token=self.bot_token)
            print("Telegram client initialized for notifications")
        except Exception as e:
            print(f"Failed to initialize Telegram client: {e}")
    
    def queue_notification(self, notification_type: str, recipient: Union[int, str, List], 
                          title: str, message: str, priority: str = "normal", 
                          metadata: Dict = None):
        """Queue notification for sending"""
        notification = {
            'id': f"notif_{int(time.time())}_{hash(message)[:8]}",
            'type': notification_type,
            'recipient': recipient,
            'title': title,
            'message': message,
            'priority': priority,
            'metadata': metadata or {},
            'timestamp': time.time(),
            'status': 'queued',
            'attempts': 0
        }
        
        with self.queue_lock:
            self.notification_queue.append(notification)
        
        print(f"Notification queued: {notification_type} for {recipient}")
    
    def process_notifications(self):
        """Process notification queue"""
        while self.running:
            try:
                notifications_to_process = []
                
                # Get notifications from queue
                with self.queue_lock:
                    current_time = time.time()
                    notifications_to_process = [
                        n for n in self.notification_queue 
                        if n['status'] == 'queued' and n['attempts'] < 3
                    ]
                    # Keep only recent notifications (last 24 hours)
                    self.notification_queue = [
                        n for n in self.notification_queue 
                        if current_time - n['timestamp'] < 86400
                    ]
                
                # Process each notification
                for notification in notifications_to_process:
                    try:
                        self.send_notification(notification)
                        notification['status'] = 'sent'
                        notification['sent_at'] = time.time()
                    except Exception as e:
                        notification['attempts'] += 1
                        notification['last_error'] = str(e)
                        if notification['attempts'] >= 3:
                            notification['status'] = 'failed'
                        else:
                            # Retry after delay
                            notification['next_retry'] = time.time() + (60 * notification['attempts'])
                
                # Update queue
                with self.queue_lock:
                    for n in notifications_to_process:
                        for i, qn in enumerate(self.notification_queue):
                            if qn['id'] == n['id']:
                                self.notification_queue[i] = n
                                break
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                print(f"Error in notification processor: {e}")
                time.sleep(5)
    
    def send_notification(self, notification: Dict):
        """Send notification through appropriate channel"""
        recipient = notification['recipient']
        notification_type = notification['type']
        
        # Check if notification type is enabled
        if not self.notification_config['notification_types'].get(notification_type, True):
            return
        
        # Check rate limiting
        if not self.check_rate_limit(recipient, notification_type):
            print(f"Rate limit exceeded for {recipient}")
            return
        
        # Send via appropriate channel
        if isinstance(recipient, int) or (isinstance(recipient, str) and recipient.startswith('@')):
            # Telegram notification
            self.send_telegram_notification(recipient, notification)
        
        elif isinstance(recipient, str) and '@' in recipient:
            # Email notification
            self.send_email_notification(recipient, notification)
        
        elif isinstance(recipient, str) and recipient.startswith('http'):
            # Webhook notification
            self.send_webhook_notification(recipient, notification)
        
        else:
            print(f"Unsupported recipient type: {recipient}")
    
    def send_telegram_notification(self, recipient: Union[int, str], notification: Dict):
        """Send Telegram notification"""
        if not self.telegram_client or not self.notification_config['telegram_enabled']:
            return
        
        try:
            message = f"*{notification['title']}*\n\n{notification['message']}"
            
            if notification['priority'] == 'high':
                message = f"🚨 {message}"
            elif notification['priority'] == 'medium':
                message = f"⚠️ {message}"
            else:
                message = f"ℹ️ {message}"
            
            # Add metadata if available
            if notification['metadata']:
                metadata_str = "\n\n📊 Metadata:\n"
                for key, value in notification['metadata'].items():
                    if isinstance(value, (int, float)):
                        metadata_str += f"{key}: {value}\n"
                    elif isinstance(value, str):
                        metadata_str += f"{key}: {value}\n"
                message += metadata_str
            
            asyncio.run(self._send_telegram_message(recipient, message))
            
            # Log notification
            self.log_notification(notification, 'telegram', True)
            
        except Exception as e:
            print(f"Error sending Telegram notification: {e}")
            raise
    
    async def _send_telegram_message(self, recipient: Union[int, str], message: str):
        """Send Telegram message asynchronously"""
        try:
            await self.telegram_client.send_message(recipient, message, parse_mode='markdown')
        except Exception as e:
            print(f"Async Telegram send error: {e}")
            raise
    
    def send_email_notification(self, email: str, notification: Dict):
        """Send email notification"""
        if not self.notification_config['email_enabled']:
            return
        
        try:
            # Load email configuration
            with open('email_config.json', 'r') as f:
                email_config = json.load(f)
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = notification['title']
            msg['From'] = email_config['sender_email']
            msg['To'] = email
            
            # Create HTML content
            html = f"""
            <html>
                <body>
                    <h2>{notification['title']}</h2>
                    <p>{notification['message'].replace('\n', '<br>')}</p>
            """
            
            if notification['metadata']:
                html += "<h3>Metadata:</h3><ul>"
                for key, value in notification['metadata'].items():
                    html += f"<li><strong>{key}:</strong> {value}</li>"
                html += "</ul>"
            
            html += """
                    <hr>
                    <p style="color: #666; font-size: 12px;">
                        This is an automated message from MBOT System.
                    </p>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(notification['message'], 'plain'))
            msg.attach(MIMEText(html, 'html'))
            
            # Send email
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['smtp_username'], email_config['smtp_password'])
                server.send_message(msg)
            
            # Log notification
            self.log_notification(notification, 'email', True)
            
        except Exception as e:
            print(f"Error sending email notification: {e}")
            raise
    
    def send_webhook_notification(self, webhook_url: str, notification: Dict):
        """Send webhook notification"""
        if not self.notification_config['webhook_enabled']:
            return
        
        try:
            payload = {
                'notification_id': notification['id'],
                'type': notification['type'],
                'title': notification['title'],
                'message': notification['message'],
                'priority': notification['priority'],
                'metadata': notification['metadata'],
                'timestamp': datetime.now().isoformat()
            }
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_notification(notification, 'webhook', True)
            else:
                raise Exception(f"Webhook returned {response.status_code}: {response.text}")
            
        except Exception as e:
            print(f"Error sending webhook notification: {e}")
            raise
    
    def check_rate_limit(self, recipient: Union[int, str], notification_type: str) -> bool:
        """Check rate limiting for notifications"""
        # Load rate limit data
        try:
            with open('rate_limit_data.json', 'r') as f:
                rate_data = json.load(f)
        except:
            rate_data = {}
        
        recipient_key = str(recipient)
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        
        # Initialize counters
        if recipient_key not in rate_data:
            rate_data[recipient_key] = {}
        if current_hour not in rate_data[recipient_key]:
            rate_data[recipient_key][current_hour] = {}
        
        hour_data = rate_data[recipient_key][current_hour]
        
        # Get rate limit based on recipient type
        if isinstance(recipient, int) or (isinstance(recipient, str) and str(recipient) == str(self.owner_id)):
            limit = self.notification_config['rate_limits']['admin']
        else:
            limit = self.notification_config['rate_limits']['user']
        
        # Check count
        count = hour_data.get(notification_type, 0)
        if count >= limit:
            return False
        
        # Update count
        hour_data[notification_type] = count + 1
        rate_data[recipient_key][current_hour] = hour_data
        
        # Save rate limit data
        with open('rate_limit_data.json', 'w') as f:
            json.dump(rate_data, f)
        
        return True
    
    def log_notification(self, notification: Dict, channel: str, success: bool):
        """Log notification"""
        log_entry = {
            'notification_id': notification['id'],
            'type': notification['type'],
            'recipient': str(notification['recipient']),
            'channel': channel,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'priority': notification['priority']
        }
        
        try:
            with open('notification_logs.json', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Error logging notification: {e}")
    
    # Convenience Methods
    
    def notify_boost_completed(self, user_id: int, boost_id: str, video_url: str, 
                              delivered: int, target: int, duration: float):
        """Notify user about completed boost"""
        title = "✅ Boost Completed"
        message = f"""
Your boost has been completed successfully!

📹 Video: {video_url}
🎯 Target: {target} views
✅ Delivered: {delivered} views
⏱️ Duration: {duration:.1f} seconds

Thank you for using MBOT!
"""
        
        metadata = {
            'boost_id': boost_id,
            'video_url': video_url,
            'target_count': target,
            'delivered_count': delivered,
            'duration': duration
        }
        
        self.queue_notification(
            'boost_completed',
            user_id,
            title,
            message,
            'normal',
            metadata
        )
    
    def notify_boost_failed(self, user_id: int, boost_id: str, video_url: str, 
                           error_message: str):
        """Notify user about failed boost"""
        title = "❌ Boost Failed"
        message = f"""
Your boost has failed!

📹 Video: {video_url}
❌ Error: {error_message}

Our team has been notified and will investigate the issue.
You can try again in a few minutes.
"""
        
        metadata = {
            'boost_id': boost_id,
            'video_url': video_url,
            'error': error_message
        }
        
        self.queue_notification(
            'boost_failed',
            user_id,
            title,
            message,
            'high',
            metadata
        )
        
        # Also notify admin
        self.notify_admin_security(
            "Boost Failure",
            f"Boost {boost_id} failed for user {user_id}",
            metadata
        )
    
    def notify_new_user(self, user_id: int, username: str, first_name: str):
        """Notify admin about new user"""
        title = "👤 New User Registered"
        message = f"""
New user has registered on MBOT:

🆔 User ID: {user_id}
👤 Username: @{username}
📛 Name: {first_name}
⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        metadata = {
            'user_id': user_id,
            'username': username,
            'first_name': first_name,
            'timestamp': datetime.now().isoformat()
        }
        
        self.queue_notification(
            'new_user',
            self.owner_id,
            title,
            message,
            'normal',
            metadata
        )
    
    def notify_admin_security(self, alert_type: str, description: str, details: Dict = None):
        """Notify admin about security alert"""
        if not self.owner_id:
            return
        
        title = f"🚨 Security Alert: {alert_type}"
        message = f"""
Security alert detected:

🔔 Type: {alert_type}
📝 Description: {description}
⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Please review the security logs for details.
"""
        
        self.queue_notification(
            'security_alert',
            self.owner_id,
            title,
            message,
            'high',
            details
        )
    
    def notify_system_alert(self, component: str, issue: str, severity: str = 'medium'):
        """Notify about system alert"""
        title = f"⚠️ System Alert: {component}"
        message = f"""
System alert detected:

🔧 Component: {component}
📊 Issue: {issue}
🚨 Severity: {severity}
⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Please check the system logs for details.
"""
        
        priority = 'high' if severity in ['high', 'critical'] else 'medium'
        
        self.queue_notification(
            'system_alert',
            self.owner_id,
            title,
            message,
            priority,
            {'component': component, 'issue': issue, 'severity': severity}
        )
    
    def send_promotional_message(self, user_ids: List[int], message: str):
        """Send promotional message to multiple users"""
        title = "🎉 Special Announcement"
        
        for user_id in user_ids:
            self.queue_notification(
                'promotional',
                user_id,
                title,
                message,
                'normal',
                {'campaign': 'promotional', 'timestamp': datetime.now().isoformat()}
            )
    
    def get_notification_stats(self, hours: int = 24) -> Dict:
        """Get notification statistics"""
        try:
            with open('notification_logs.json', 'r') as f:
                logs = [json.loads(line) for line in f]
        except:
            logs = []
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        recent_logs = [log for log in logs if log['timestamp'] > cutoff_time]
        
        stats = {
            'total': len(recent_logs),
            'successful': len([log for log in recent_logs if log['success']]),
            'failed': len([log for log in recent_logs if not log['success']]),
            'by_type': {},
            'by_channel': {},
            'by_priority': {}
        }
        
        for log in recent_logs:
            # Count by type
            stats['by_type'][log['type']] = stats['by_type'].get(log['type'], 0) + 1
            
            # Count by channel
            stats['by_channel'][log['channel']] = stats['by_channel'].get(log['channel'], 0) + 1
            
            # Count by priority
            priority = log.get('priority', 'normal')
            stats['by_priority'][priority] = stats['by_priority'].get(priority, 0) + 1
        
        return stats
    
    def stop(self):
        """Stop notification system"""
        self.running = False
        if self.telegram_client:
            self.telegram_client.disconnect()

# Global instance (will be initialized in main.py)
notification_system = None

def init_notification_system(bot_token: str, owner_id: int):
    """Initialize global notification system"""
    global notification_system
    notification_system = NotificationSystem(bot_token, owner_id)
    return notification_system
