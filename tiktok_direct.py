"""
Direct TikTok API Communication
No External APIs - Pure TikTok Server Connection
"""

import aiohttp
import asyncio
import time
import random
import hashlib  # ADDED THIS IMPORT
import json
from typing import Dict, Optional, List
import urllib.parse
from fake_useragent import UserAgent

class TikTokDirectAPI:
    def __init__(self, config: Dict):
        self.config = config
        self.ua = UserAgent()
        self.devices = []
        self.proxies = []
        self.session_pool = []
        self.load_devices()
        self.load_proxies()
        
    def load_devices(self):
        """Load devices from devices.txt"""
        try:
            with open('devices.txt', 'r') as f:
                for line in f:
                    if line.strip():
                        parts = line.strip().split(':')
                        if len(parts) >= 6:
                            device = {
                                'device_id': parts[0],
                                'install_id': parts[1],
                                'openudid': parts[2],
                                'device_model': parts[3],
                                'os_version': parts[4],
                                'version_code': parts[5]
                            }
                            self.devices.append(device)
        except:
            # Create default devices if file not found
            self._create_default_devices()
    
    def _create_default_devices(self):
        """Create default devices"""
        for i in range(50):
            device = {
                'device_id': str(random.randint(1000000000000000000, 9999999999999999999)),
                'install_id': str(random.randint(1000000000000000000, 9999999999999999999)),
                'openudid': hashlib.md5(str(time.time()).encode()).hexdigest().upper(),
                'device_model': random.choice(['iPhone14,2', 'SM-G998B', 'iPhone13,3']),
                'os_version': random.choice(['16.5', '13', '15.4']),
                'version_code': random.choice(['23.6.0', '29.2.4', '22.8.0'])
            }
            self.devices.append(device)
    
    def load_proxies(self):
        """Load proxies from proxies.txt"""
        try:
            with open('proxies.txt', 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
        except:
            self.proxies = []
    
    def get_random_device(self) -> Dict:
        """Get random device fingerprint"""
        return random.choice(self.devices) if self.devices else self._create_default_device()
    
    def get_random_proxy(self) -> Optional[str]:
        """Get random proxy"""
        return random.choice(self.proxies) if self.proxies else None
    
    def _create_default_device(self) -> Dict:
        """Create a default device"""
        return {
            'device_id': str(random.randint(1000000000000000000, 9999999999999999999)),
            'install_id': str(random.randint(1000000000000000000, 9999999999999999999)),
            'openudid': hashlib.md5(str(time.time()).encode()).hexdigest().upper(),
            'device_model': 'iPhone14,2',
            'os_version': '16.5',
            'version_code': '23.6.0'
        }
    
    def generate_headers(self, device: Dict) -> Dict:
        """Generate TikTok headers"""
        headers = {
            'User-Agent': f'com.ss.android.ugc.trill/{device["version_code"]} '
                         f'(Linux; U; Android {device["os_version"]}; {device["device_model"]}; '
                         f'Build/; Cronet/TTNetVersion:)',
            'Accept-Encoding': 'gzip',
            'X-Tt-Token': self._generate_token(),
            'X-SS-Stub': self._generate_signature(),
            'X-Gorgon': self._generate_gorgon(),
            'X-Khronos': str(int(time.time())),
            'sdk-version': '1',
            'x-tt-trace-id': self._generate_trace_id(),
            'x-tt-store-region': 'us',
            'x-tt-store-region-src': 'did',
            'passport-sdk-version': '19',
            'host': 'api16-normal-c-useast1a.tiktokv.com',
            'connection': 'Keep-Alive'
        }
        return headers
    
    def _generate_token(self) -> str:
        """Generate X-Tt-Token"""
        chars = 'abcdef0123456789'
        return ''.join(random.choices(chars, k=32))
    
    def _generate_signature(self) -> str:
        """Generate X-SS-Stub"""
        chars = 'ABCDEF0123456789'
        return ''.join(random.choices(chars, k=16))
    
    def _generate_gorgon(self) -> str:
        """Generate X-Gorgon"""
        chars = '0123456789abcdef'
        return ''.join(random.choices(chars, k=40))
    
    def _generate_trace_id(self) -> str:
        """Generate trace ID"""
        timestamp = int(time.time() * 1000)
        random_num = random.randint(1000000000, 9999999999)
        return f'{timestamp:016x}{random_num:010x}'
    
    async def send_like(self, video_id: str) -> bool:
        """
        Send a like to TikTok video
        Returns: True if successful
        """
        try:
            device = self.get_random_device()
            proxy = self.get_random_proxy()
            
            headers = self.generate_headers(device)
            
            # TikTok like endpoint
            endpoint = random.choice(self.config['tiktok']['api_endpoints'])
            url = f"{endpoint}/aweme/v1/aweme/commit/item/digg/"
            
            # Prepare payload
            payload = {
                'aweme_id': video_id,
                'type': '1',  # 1 for like
                'channel_id': '3',
                'os_version': device['os_version'],
                'version_code': device['version_code'],
                'device_id': device['device_id'],
                'iid': device['install_id'],
                'device_type': device['device_model'],
                'channel': 'googleplay',
                'account_region': 'US',
                'app_language': 'en',
                'app_type': 'normal',
                'sys_region': 'US',
                'carrier_region': 'US',
                'locale': 'en_US',
                'op_region': 'US',
                'ac': 'wifi',
                'current_region': 'US',
                'aid': '1180',
                'app_name': 'trill',
                'version_name': device['version_code'],
                'device_brand': 'Apple' if 'iPhone' in device['device_model'] else 'samsung',
                'device_platform': 'iphone' if 'iPhone' in device['device_model'] else 'android',
                'resolution': '1170*2532' if 'iPhone' in device['device_model'] else '1080*2400',
                'dpi': 480,
                'update_version_code': device['version_code'],
                '_rticket': str(int(time.time() * 1000)),
                'ts': str(int(time.time()))
            }
            
            # Setup proxy if available
            proxy_config = None
            if proxy:
                proxy_config = proxy
            
            # Create session
            timeout = aiohttp.ClientTimeout(total=self.config['tiktok']['request_timeout'])
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            ) as session:
                
                async with session.post(
                    url,
                    headers=headers,
                    data=payload,
                    proxy=proxy_config
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        if data.get('status_code') == 0:
                            return True
                    
            return False
            
        except Exception as e:
            print(f"Like error: {e}")
            return False
    
    async def check_video_exists(self, video_id: str) -> bool:
        """Check if video exists"""
        try:
            device = self.get_random_device()
            headers = self.generate_headers(device)
            
            endpoint = random.choice(self.config['tiktok']['api_endpoints'])
            url = f"{endpoint}/aweme/v1/aweme/detail/?aweme_id={video_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('aweme_detail') is not None
            
            return False
            
        except:
            return False
    
    async def get_video_info(self, video_id: str) -> Optional[Dict]:
        """Get video information"""
        try:
            device = self.get_random_device()
            headers = self.generate_headers(device)
            
            endpoint = random.choice(self.config['tiktok']['api_endpoints'])
            url = f"{endpoint}/aweme/v1/aweme/detail/?aweme_id={video_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('aweme_detail', {})
            
            return None
            
        except:
            return None
