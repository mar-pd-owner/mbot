"""
MBOT Boost Manager - Core Boosting Engine
Ultra-fast TikTok view/like boosting system
"""

import asyncio
import time
import random
import threading
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime
import hashlib
from anti_detect import anti_detect
from encryption import encryption

class BoostManager:
    def __init__(self, max_threads: int = 100):
        self.max_threads = max_threads
        self.active = False
        self.current_boost = None
        self.stats_lock = threading.Lock()
        self.boost_stats = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=max_threads)
        self.devices = []
        self.proxies = []
        self.rate_limiter = RateLimiter()
        
        # Load resources
        self.load_devices()
        self.load_proxies()
        
        # Performance monitoring
        self.performance_data = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'avg_response_time': 0,
            'peak_rps': 0,
            'total_bandwidth': 0
        }
    
    def load_devices(self):
        """Load device list"""
        try:
            with open('devices.txt', 'r') as f:
                self.devices = [line.strip() for line in f if line.strip()]
            print(f"Loaded {len(self.devices)} devices")
        except Exception as e:
            print(f"Error loading devices: {e}")
            self.devices = []
    
    def load_proxies(self):
        """Load proxy list"""
        try:
            with open('proxies.txt', 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            if self.proxies:
                print(f"Loaded {len(self.proxies)} proxies")
        except:
            self.proxies = []
    
    async def boost_video(self, video_url: str, count: int, boost_type: str = "views") -> Dict:
        """Main boost function"""
        self.active = True
        video_id = self.extract_video_id(video_url)
        
        if not video_id:
            return {"success": False, "error": "Invalid video URL"}
        
        # Initialize boost session
        boost_session = {
            'video_id': video_id,
            'video_url': video_url,
            'target_count': count,
            'boost_type': boost_type,
            'start_time': time.time(),
            'end_time': None,
            'status': 'running',
            'completed': 0,
            'failed': 0,
            'current_rps': 0,
            'workers': []
        }
        
        self.current_boost = boost_session
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_boost)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start workers
        workers_needed = min(self.max_threads, count // 10 + 1)
        workers = []
        
        for i in range(workers_needed):
            worker = BoostWorker(
                worker_id=i,
                video_id=video_id,
                boost_type=boost_type,
                manager=self
            )
            workers.append(worker)
            worker.start()
        
        # Wait for completion
        try:
            while (self.active and 
                   boost_session['completed'] < count and 
                   time.time() - boost_session['start_time'] < 300):  # 5 minute timeout
                
                await asyncio.sleep(0.5)
                
                # Update progress
                with self.stats_lock:
                    boost_session['completed'] = self.boost_stats.get('successful', 0)
                    boost_session['failed'] = self.boost_stats.get('failed', 0)
                    boost_session['current_rps'] = self.boost_stats.get('current_rps', 0)
                
                # Check if we should stop
                if not self.active:
                    break
        except Exception as e:
            print(f"Boost error: {e}")
        
        # Stop workers
        for worker in workers:
            worker.stop()
        
        # Finalize
        boost_session['end_time'] = time.time()
        boost_session['status'] = 'completed' if boost_session['completed'] >= count else 'stopped'
        
        result = {
            'success': boost_session['status'] == 'completed',
            'video_id': video_id,
            'requested': count,
            'delivered': boost_session['completed'],
            'failed': boost_session['failed'],
            'duration': boost_session['end_time'] - boost_session['start_time'],
            'average_rps': boost_session['completed'] / (boost_session['end_time'] - boost_session['start_time']) if boost_session['end_time'] > boost_session['start_time'] else 0,
            'peak_rps': self.performance_data['peak_rps']
        }
        
        # Save boost log
        self.save_boost_log(result)
        
        return result
    
    def monitor_boost(self):
        """Monitor boost performance"""
        last_count = 0
        last_time = time.time()
        
        while self.active and self.current_boost:
            time.sleep(1)
            
            with self.stats_lock:
                current_count = self.boost_stats.get('successful', 0)
                current_time = time.time()
                
                # Calculate RPS
                time_diff = current_time - last_time
                if time_diff > 0:
                    rps = (current_count - last_count) / time_diff
                    self.boost_stats['current_rps'] = rps
                    
                    # Update peak RPS
                    if rps > self.performance_data['peak_rps']:
                        self.performance_data['peak_rps'] = rps
                
                # Update performance data
                self.performance_data['total_requests'] = self.boost_stats.get('total_requests', 0)
                self.performance_data['successful'] = current_count
                self.performance_data['failed'] = self.boost_stats.get('failed', 0)
                
                last_count = current_count
                last_time = current_time
    
    def send_view_request(self, device_info: str, video_id: str) -> Tuple[bool, float]:
        """Send a single view request"""
        start_time = time.time()
        success = False
        response_time = 0
        
        try:
            # Get anti-detection headers
            headers = anti_detect.get_headers()
            
            # Generate device fingerprint
            fingerprint = anti_detect.generate_device_fingerprint()
            
            # Get proxy if available
            proxy = random.choice(self.proxies) if self.proxies else None
            
            # Simulate human behavior
            behavior = anti_detect.simulate_human_behavior()
            
            # Send request (this is where you'd integrate with your TikTok request system)
            # For now, simulate success
            success = random.random() > 0.1  # 90% success rate
            
            response_time = time.time() - start_time
            
            # Update stats
            with self.stats_lock:
                self.boost_stats['total_requests'] = self.boost_stats.get('total_requests', 0) + 1
                if success:
                    self.boost_stats['successful'] = self.boost_stats.get('successful', 0) + 1
                else:
                    self.boost_stats['failed'] = self.boost_stats.get('failed', 0) + 1
            
            # Update performance data
            self.performance_data['avg_response_time'] = (
                (self.performance_data['avg_response_time'] * (self.performance_data['total_requests'] - 1) + response_time) 
                / self.performance_data['total_requests']
            )
            
        except Exception as e:
            print(f"Request error: {e}")
            with self.stats_lock:
                self.boost_stats['failed'] = self.boost_stats.get('failed', 0) + 1
                self.boost_stats['total_requests'] = self.boost_stats.get('total_requests', 0) + 1
        
        return success, response_time
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from URL"""
        import re
        
        patterns = [
            r'video/(\d+)',
            r'/(\d{18,19})/',
            r'(\d{18,19})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def save_boost_log(self, result: Dict):
        """Save boost log to file"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'result': result,
                'performance': self.performance_data.copy()
            }
            
            with open('boost_logs.json', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Error saving boost log: {e}")
    
    def get_performance_report(self) -> Dict:
        """Get performance report"""
        with self.stats_lock:
            return {
                'current_boost': self.current_boost,
                'performance': self.performance_data.copy(),
                'boost_stats': self.boost_stats.copy(),
                'devices_available': len(self.devices),
                'proxies_available': len(self.proxies),
                'active_workers': threading.active_count() - 1
            }
    
    def stop_all(self):
        """Stop all boosting activities"""
        self.active = False
        self.thread_pool.shutdown(wait=False)
        
        if self.current_boost:
            self.current_boost['status'] = 'stopped'
            self.current_boost['end_time'] = time.time()

class BoostWorker(threading.Thread):
    """Individual boost worker thread"""
    
    def __init__(self, worker_id: int, video_id: str, boost_type: str, manager):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.video_id = video_id
        self.boost_type = boost_type
        self.manager = manager
        self.running = True
        
    def run(self):
        """Worker main loop"""
        while self.running and self.manager.active:
            try:
                # Get random device
                if not self.manager.devices:
                    time.sleep(1)
                    continue
                
                device = random.choice(self.manager.devices)
                
                # Apply rate limiting
                self.manager.rate_limiter.wait()
                
                # Send request
                success, response_time = self.manager.send_view_request(device, self.video_id)
                
                # Random delay between requests
                delay = random.uniform(0.01, 0.1)
                time.sleep(delay)
                
            except Exception as e:
                print(f"Worker {self.worker_id} error: {e}")
                time.sleep(0.5)
    
    def stop(self):
        """Stop worker"""
        self.running = False

class RateLimiter:
    """Rate limiter for requests"""
    
    def __init__(self, max_rps: int = 100):
        self.max_rps = max_rps
        self.min_interval = 1.0 / max_rps
        self.last_request = 0
        self.lock = threading.Lock()
    
    def wait(self):
        """Wait if needed to maintain rate limit"""
        with self.lock:
            current_time = time.time()
            time_since_last = current_time - self.last_request
            
            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)
            
            self.last_request = time.time()

# Global instance
boost_manager = BoostManager(max_threads=100)
