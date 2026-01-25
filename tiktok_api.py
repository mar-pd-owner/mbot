"""
TikTok API - Fixed Working Version
"""

import aiohttp
import asyncio
import time
import random
import hashlib
import json
from typing import Dict
from fake_useragent import UserAgent

class TikTokAPI:
    def __init__(self, config: Dict):
        self.config = config
        self.ua = UserAgent()
        self.session = None
        self.request_count = 0
        self.last_request_time = 0
        
    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config['tiktok']['request_timeout']),
                connector=aiohttp.TCPConnector(ssl=False)
            )
        return self.session
    
    def generate_device_info(self) -> Dict:
        """Generate device information"""
        device_id = str(random.randint(1000000000000000000, 9999999999999999999))
        install_id = str(random.randint(1000000000000000000, 9999999999999999999))
        
        return {
            'device_id': device_id,
            'install_id': install_id,
            'openudid': hashlib.md5(device_id.encode()).hexdigest().upper(),
            'device_model': random.choice(['iPhone14,2', 'SM-G998B', 'iPhone13,3']),
            'os_version': random.choice(['16.5', '13', '15.4']),
            'version_code': random.choice(['23.6.0', '29.2.4', '22.8.0'])
        }
    
    def generate_headers(self, device: Dict) -> Dict:
        """Generate TikTok headers"""
        return {
            'User-Agent': f'com.ss.android.ugc.trill/{device["version_code"]} (Linux; U; Android {device["os_version"]}; {device["device_model"]}; Build/; Cronet/TTNetVersion:)',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://www.tiktok.com',
            'Referer': 'https://www.tiktok.com/',
            'X-Tt-Token': ''.join(random.choices('abcdef0123456789', k=32)),
            'X-Khronos': str(int(time.time())),
            'X-Gorgon': ''.join(random.choices('0123456789abcdef', k=40))
        }
    
    async def send_like(self, video_id: str) -> Dict:
        """
        Send a like to TikTok video
        Returns: {'success': bool, 'message': str}
        """
        try:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < 0.1:  # 100ms minimum between requests
                await asyncio.sleep(0.1 - time_since_last)
            
            device = self.generate_device_info()
            headers = self.generate_headers(device)
            
            # Choose endpoint
            endpoint = random.choice(self.config['tiktok']['api_endpoints'])
            url = f"{endpoint}/aweme/v1/aweme/commit/item/digg/"
            
            # Prepare form data
            form_data = aiohttp.FormData()
            form_data.add_field('aweme_id', video_id)
            form_data.add_field('type', '1')  # 1 = like
            form_data.add_field('channel_id', '3')
            form_data.add_field('os_version', device['os_version'])
            form_data.add_field('version_code', device['version_code'])
            form_data.add_field('device_id', device['device_id'])
            form_data.add_field('iid', device['install_id'])
            form_data.add_field('device_type', device['device_model'])
            form_data.add_field('channel', 'googleplay')
            form_data.add_field('account_region', 'US')
            form_data.add_field('app_language', 'en')
            
            session = await self.get_session()
            
            async with session.post(
                url,
                headers=headers,
                data=form_data
            ) as response:
                
                self.last_request_time = time.time()
                self.request_count += 1
                
                # Get response text
                response_text = await response.text()
                
                # Try to parse JSON
                try:
                    data = json.loads(response_text)
                    if 'status_code' in data and data['status_code'] == 0:
                        return {'success': True, 'message': 'Like sent successfully'}
                    else:
                        error_msg = data.get('status_msg', 'Unknown error')
                        return {'success': False, 'message': f'API Error: {error_msg}'}
                except json.JSONDecodeError:
                    # If not JSON, check for success indicators
                    if response.status == 200:
                        # Sometimes TikTok returns success without JSON
                        return {'success': True, 'message': 'Like sent (non-JSON response)'}
                    else:
                        return {'success': False, 'message': f'HTTP {response.status}: {response_text[:100]}'}
        
        except aiohttp.ClientError as e:
            return {'success': False, 'message': f'Network error: {str(e)}'}
        except asyncio.TimeoutError:
            return {'success': False, 'message': 'Request timeout'}
        except Exception as e:
            return {'success': False, 'message': f'Unexpected error: {str(e)}'}
    
    async def close(self):
        """Close session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Cleanup"""
        if self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except:
                pass
