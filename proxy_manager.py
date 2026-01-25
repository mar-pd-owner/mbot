"""
Proxy Manager - Handle proxy rotation and validation
"""

import aiohttp
import asyncio
import time
import random
from typing import List, Dict, Optional
import urllib.parse

class ProxyManager:
    def __init__(self, proxy_file: str = "proxies.txt"):
        self.proxy_file = proxy_file
        self.proxies = []
        self.valid_proxies = []
        self.proxy_stats = {}
        self.last_check = 0
        self.check_interval = 300  # 5 minutes
        self.load_proxies()
    
    def load_proxies(self):
        """Load proxies from file"""
        try:
            with open(self.proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            
            print(f"✅ Loaded {len(self.proxies)} proxies from {self.proxy_file}")
            
            # Validate proxies on startup
            if self.proxies:
                asyncio.create_task(self.validate_all_proxies())
                
        except FileNotFoundError:
            print(f"⚠️ Proxy file {self.proxy_file} not found")
            self.proxies = []
            self.valid_proxies = []
    
    async def validate_proxy(self, proxy: str) -> bool:
        """Validate if proxy is working"""
        try:
            test_url = "https://api16-normal-c-useast1a.tiktokv.com"
            
            timeout = aiohttp.ClientTimeout(total=10)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    test_url,
                    proxy=proxy,
                    headers={'User-Agent': 'Mozilla/5.0'}
                ) as response:
                    if response.status < 400:
                        return True
        
        except Exception as e:
            pass
        
        return False
    
    async def validate_all_proxies(self):
        """Validate all proxies"""
        print("🔍 Validating proxies...")
        
        tasks = []
        for proxy in self.proxies:
            task = self.validate_proxy(proxy)
            tasks.append((proxy, task))
        
        self.valid_proxies = []
        valid_count = 0
        
        for proxy, task in tasks:
            try:
                is_valid = await task
                if is_valid:
                    self.valid_proxies.append(proxy)
                    valid_count += 1
                    print(f"  ✅ {proxy}")
                else:
                    print(f"  ❌ {proxy}")
            except:
                print(f"  ❌ {proxy}")
        
        print(f"📊 {valid_count}/{len(self.proxies)} proxies validated")
        self.last_check = time.time()
    
    def get_proxy(self) -> Optional[str]:
        """Get a random valid proxy"""
        if not self.valid_proxies:
            # Check if we need to re-validate
            if time.time() - self.last_check > self.check_interval:
                asyncio.create_task(self.validate_all_proxies())
            
            # Fallback to any proxy
            return random.choice(self.proxies) if self.proxies else None
        
        # Use weighted random selection based on success rate
        proxy = random.choice(self.valid_proxies)
        
        # Update stats
        proxy_key = self._get_proxy_key(proxy)
        self.proxy_stats[proxy_key] = self.proxy_stats.get(proxy_key, {
            'success': 0,
            'fail': 0,
            'last_used': 0
        })
        
        self.proxy_stats[proxy_key]['last_used'] = time.time()
        
        return proxy
    
    def get_batch_proxies(self, count: int) -> List[str]:
        """Get multiple proxies for batch processing"""
        proxies = []
        
        for _ in range(count):
            proxy = self.get_proxy()
            if proxy and proxy not in proxies:  # Avoid duplicates in batch
                proxies.append(proxy)
        
        # If not enough unique proxies, allow duplicates
        while len(proxies) < count and self.valid_proxies:
            proxy = random.choice(self.valid_proxies)
            proxies.append(proxy)
        
        return proxies
    
    def report_success(self, proxy: str):
        """Report successful proxy usage"""
        proxy_key = self._get_proxy_key(proxy)
        if proxy_key in self.proxy_stats:
            self.proxy_stats[proxy_key]['success'] += 1
    
    def report_failure(self, proxy: str):
        """Report failed proxy usage"""
        proxy_key = self._get_proxy_key(proxy)
        if proxy_key in self.proxy_stats:
            self.proxy_stats[proxy_key]['fail'] += 1
            
            # Too many failures, remove from valid list
            stats = self.proxy_stats[proxy_key]
            total = stats['success'] + stats['fail']
            failure_rate = stats['fail'] / total if total > 0 else 0
            
            if failure_rate > 0.8:  # 80% failure rate
                if proxy in self.valid_proxies:
                    self.valid_proxies.remove(proxy)
                    print(f"⚠️ Removed proxy {proxy} (failure rate: {failure_rate:.0%})")
    
    def _get_proxy_key(self, proxy: str) -> str:
        """Get proxy key for stats"""
        return proxy.split('@')[-1] if '@' in proxy else proxy
    
    def add_proxy(self, proxy: str):
        """Add a new proxy"""
        if proxy not in self.proxies:
            self.proxies.append(proxy)
            self.save_proxies()
            
            # Validate new proxy
            asyncio.create_task(self._validate_and_add(proxy))
    
    async def _validate_and_add(self, proxy: str):
        """Validate and add proxy to valid list"""
        is_valid = await self.validate_proxy(proxy)
        if is_valid and proxy not in self.valid_proxies:
            self.valid_proxies.append(proxy)
    
    def remove_proxy(self, proxy: str):
        """Remove a proxy"""
        if proxy in self.proxies:
            self.proxies.remove(proxy)
        
        if proxy in self.valid_proxies:
            self.valid_proxies.remove(proxy)
        
        self.save_proxies()
    
    def save_proxies(self):
        """Save proxies to file"""
        with open(self.proxy_file, 'w') as f:
            f.write('\n'.join(self.proxies))
        
        print(f"💾 Saved {len(self.proxies)} proxies to {self.proxy_file}")
    
    def get_stats(self) -> Dict:
        """Get proxy statistics"""
        total = len(self.proxies)
        valid = len(self.valid_proxies)
        
        # Calculate success rates
        success_rates = {}
        for proxy_key, stats in self.proxy_stats.items():
            total_attempts = stats['success'] + stats['fail']
            if total_attempts > 0:
                success_rate = stats['success'] / total_attempts
                success_rates[proxy_key] = f"{success_rate:.1%}"
        
        return {
            "total_proxies": total,
            "valid_proxies": valid,
            "validity_rate": f"{(valid/total*100):.1f}%" if total > 0 else "0%",
            "last_validation": time.strftime('%H:%M:%S', time.localtime(self.last_check)),
            "success_rates": success_rates
        }
