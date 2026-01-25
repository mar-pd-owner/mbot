"""
Short URL Handler - vt.tiktok.com | vm.tiktok.com
Direct TikTok Video ID Extraction
"""

import re
import asyncio
import aiohttp
from typing import Optional, Dict
import urllib.parse

class ShortURLHandler:
    def __init__(self):
        self.url_patterns = [
            r'vt\.tiktok\.com/([A-Za-z0-9]+)',
            r'vm\.tiktok\.com/([A-Za-z0-9]+)',
            r'tiktok\.com/@[^/]+/video/(\d+)',
            r'tiktok\.com/t/([A-Za-z0-9]+)'
        ]
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def extract_video_id(self, short_url: str) -> Optional[str]:
        """
        Extract TikTok video ID from any short URL
        Supports: vt.tiktok.com, vm.tiktok.com, tiktok.com/t/
        """
        # Clean URL
        if not short_url.startswith('http'):
            short_url = 'https://' + short_url
        
        try:
            # Try direct pattern matching first
            video_id = self._extract_from_pattern(short_url)
            if video_id:
                return video_id
            
            # If pattern fails, fetch and extract
            async with aiohttp.ClientSession() as session:
                async with session.get(short_url, headers=self.headers, allow_redirects=True) as response:
                    if response.status == 200:
                        final_url = str(response.url)
                        return self._extract_from_final_url(final_url)
                    
            return None
            
        except Exception as e:
            print(f"Error extracting video ID: {e}")
            return None
    
    def _extract_from_pattern(self, url: str) -> Optional[str]:
        """Extract video ID from URL patterns"""
        for pattern in self.url_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _extract_from_final_url(self, final_url: str) -> Optional[str]:
        """Extract from final redirected URL"""
        # Pattern: /video/7123456789012345678
        video_match = re.search(r'/video/(\d+)', final_url)
        if video_match:
            return video_match.group(1)
        
        # Pattern: /v/123456789012345678
        v_match = re.search(r'/v/(\d+)', final_url)
        if v_match:
            return v_match.group(1)
        
        return None
    
    async def batch_extract(self, urls: list) -> Dict[str, Optional[str]]:
        """Extract multiple video IDs at once"""
        results = {}
        tasks = []
        
        for url in urls:
            task = self.extract_video_id(url)
            tasks.append((url, task))
        
        for url, task in tasks:
            try:
                video_id = await task
                results[url] = video_id
            except:
                results[url] = None
        
        return results
    
    def validate_short_url(self, url: str) -> bool:
        """Validate if URL is a TikTok short URL"""
        patterns = [
            'vt.tiktok.com',
            'vm.tiktok.com',
            'tiktok.com/t/',
            'tiktok.com/@'
        ]
        
        return any(pattern in url for pattern in patterns)


# Example usage
async def test():
    handler = ShortURLHandler()
    
    test_urls = [
        "https://vt.tiktok.com/ZSRLRsxrK/",
        "https://vm.tiktok.com/ZSRLCgYxv/",
        "tiktok.com/@user/video/1234567890123456789",
        "https://www.tiktok.com/t/ZSRLCgYxv/"
    ]
    
    for url in test_urls:
        video_id = await handler.extract_video_id(url)
        print(f"URL: {url}")
        print(f"Video ID: {video_id}")
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test())
