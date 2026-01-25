"""
Advanced Anti-Detection System
Prevents TikTok from detecting bot activities
"""

import random
import time
import hashlib
import json
from urllib.parse import urlparse, parse_qs
import socket
import struct

class AntiDetectionSystem:
    def __init__(self):
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Mobile/15E148 Safari/604.1'
        ]
        
        self.referers = [
            'https://www.tiktok.com/',
            'https://m.tiktok.com/',
            'https://vt.tiktok.com/',
            'https://www.google.com/',
            'https://www.youtube.com/'
        ]
        
        self.device_ids = []
        self.session_rotation = 0
        
        # Load evasion patterns
        self.load_evasion_patterns()
    
    def load_evasion_patterns(self):
        """Load evasion patterns from file"""
        try:
            with open('evasion_patterns.json', 'r') as f:
                self.patterns = json.load(f)
        except:
            self.patterns = {
                "request_delays": [0.1, 0.2, 0.3, 0.5, 0.8, 1.0],
                "header_variations": 10,
                "ip_rotation": True,
                "device_fingerprinting": True
            }
    
    def get_random_user_agent(self):
        """Get random user agent"""
        return random.choice(self.user_agents)
    
    def get_random_referer(self):
        """Get random referer"""
        return random.choice(self.referers)
    
    def generate_device_fingerprint(self):
        """Generate unique device fingerprint"""
        fingerprint = {
            'screen_resolution': f"{random.randint(360, 3840)}x{random.randint(640, 2160)}",
            'color_depth': random.choice([16, 24, 30, 32]),
            'timezone': random.choice(['Asia/Dhaka', 'UTC', 'America/New_York', 'Europe/London']),
            'language': random.choice(['en-US', 'en-GB', 'bn-BD', 'es-ES']),
            'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
            'hardware_concurrency': random.choice([2, 4, 8, 16]),
            'device_memory': random.choice([4, 8, 16, 32]),
            'max_touch_points': random.choice([0, 5, 10])
        }
        
        # Add canvas fingerprint
        canvas_hash = hashlib.md5(str(random.getrandbits(128)).encode()).hexdigest()
        fingerprint['canvas_hash'] = canvas_hash
        
        return fingerprint
    
    def get_random_delay(self):
        """Get random request delay"""
        return random.choice(self.patterns['request_delays'])
    
    def rotate_session(self):
        """Rotate session to avoid detection"""
        self.session_rotation += 1
        
        if self.session_rotation >= 100:
            self.session_rotation = 0
            return True  # Signal to rotate
        
        return False
    
    def generate_request_signature(self, url, data=None):
        """Generate unique request signature"""
        timestamp = int(time.time())
        nonce = random.getrandbits(64)
        
        # Create signature base
        base = f"{url}:{timestamp}:{nonce}"
        if data:
            base += f":{json.dumps(data, sort_keys=True)}"
        
        # Hash with multiple algorithms
        md5_hash = hashlib.md5(base.encode()).hexdigest()
        sha256_hash = hashlib.sha256(base.encode()).hexdigest()
        
        signature = {
            'ts': timestamp,
            'nonce': nonce,
            'sig': sha256_hash[:16],
            'hash': md5_hash
        }
        
        return signature
    
    def obfuscate_url(self, url):
        """Obfuscate URL parameters"""
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Add random parameters
        query_params['_t'] = [str(int(time.time()))]
        query_params['_r'] = [str(random.getrandbits(32))]
        query_params['_v'] = ['1']
        
        # Rebuild URL
        new_query = '&'.join([f"{k}={v[0]}" for k, v in query_params.items()])
        new_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"
        
        return new_url
    
    def get_headers(self):
        """Generate realistic headers"""
        user_agent = self.get_random_user_agent()
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'TE': 'trailers'
        }
        
        # Add random referer sometimes
        if random.random() > 0.3:
            headers['Referer'] = self.get_random_referer()
        
        return headers
    
    def simulate_human_behavior(self):
        """Simulate human-like behavior patterns"""
        behaviors = [
            self.simulate_scrolling,
            self.simulate_mouse_movement,
            self.simulate_typing,
            self.simulate_reading_time
        ]
        
        behavior = random.choice(behaviors)
        return behavior()
    
    def simulate_scrolling(self):
        """Simulate scrolling behavior"""
        scroll_delay = random.uniform(0.5, 2.0)
        scroll_steps = random.randint(3, 10)
        return {'action': 'scroll', 'delay': scroll_delay, 'steps': scroll_steps}
    
    def simulate_mouse_movement(self):
        """Simulate mouse movement"""
        movements = random.randint(2, 8)
        return {'action': 'mouse_move', 'movements': movements}
    
    def simulate_typing(self):
        """Simulate typing behavior"""
        typing_delay = random.uniform(0.1, 0.5)
        return {'action': 'typing', 'delay': typing_delay}
    
    def simulate_reading_time(self):
        """Simulate reading time"""
        reading_time = random.uniform(2.0, 10.0)
        return {'action': 'reading', 'time': reading_time}
    
    def generate_device_id(self):
        """Generate realistic device ID"""
        prefixes = ['SM-', 'iPhone', 'Pixel', 'OnePlus', 'Xiaomi']
        prefix = random.choice(prefixes)
        
        if prefix == 'SM-':
            model = f"G{random.randint(970, 998)}N"
        elif prefix == 'iPhone':
            model = f"{random.randint(8, 14)}"
        else:
            model = f"{random.randint(1, 10)}"
        
        serial = ''.join(random.choices('0123456789ABCDEF', k=12))
        
        return f"{prefix}{model}:{serial}"
    
    def get_ip_rotation(self):
        """Get IP rotation strategy"""
        strategies = [
            'proxy_chain',
            'tor_network',
            'vpn_rotation',
            'mobile_data'
        ]
        
        return random.choice(strategies)
    
    def detect_bot_patterns(self, request_history):
        """Detect bot-like patterns in request history"""
        if len(request_history) < 10:
            return False
        
        # Check for consistent timing
        timings = [r['timestamp'] for r in request_history[-10:]]
        intervals = [timings[i+1] - timings[i] for i in range(len(timings)-1)]
        
        # If intervals are too consistent, might be bot
        if max(intervals) - min(intervals) < 0.1:
            return True
        
        # Check for identical request patterns
        urls = [r['url'] for r in request_history[-10:]]
        if len(set(urls)) < 3:
            return True
        
        return False

# Global instance
anti_detect = AntiDetectionSystem()
