"""
Core Engine - Handles Short URLs and Likes
"""

import asyncio
import time
import random
from typing import List, Dict
from short_url_handler import ShortURLHandler
from tiktok_direct import TikTokDirectAPI
from speed_booster import SpeedBooster

class MBotCore:
    def __init__(self, config: Dict):
        self.config = config
        self.url_handler = ShortURLHandler()
        self.tiktok_api = TikTokDirectAPI(config)
        self.speed_booster = SpeedBooster()
        self.active_tasks = {}
        self.stats = {
            "total_likes_sent": 0,
            "total_videos": 0,
            "success_rate": 0.0,
            "last_activity": time.time()
        }
    
    async def send_likes(self, short_url: str, like_count: int = 500) -> Dict:
        """
        Send likes to a TikTok video using short URL
        """
        print(f"🎯 Processing: {short_url}")
        print(f"🎯 Target Likes: {like_count}")
        
        # Step 1: Extract Video ID
        print("📦 Extracting video ID...")
        video_id = await self.url_handler.extract_video_id(short_url)
        
        if not video_id:
            return {
                "status": "error",
                "message": "Failed to extract video ID",
                "video_id": None
            }
        
        print(f"✅ Video ID: {video_id}")
        
        # Step 2: Activate Speed Booster
        print("⚡ Activating speed booster...")
        self.speed_booster.activate()
        
        # Step 3: Send Likes
        print(f"🚀 Sending {like_count} likes...")
        start_time = time.time()
        
        results = await self._send_batch_likes(video_id, like_count)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Update statistics
        self.stats["total_likes_sent"] += results["successful"]
        self.stats["total_videos"] += 1
        self.stats["success_rate"] = (self.stats["total_likes_sent"] / 
                                     (self.stats["total_videos"] * like_count)) * 100
        
        return {
            "status": "success",
            "video_id": video_id,
            "requested_likes": like_count,
            "sent_likes": results["successful"],
            "failed_likes": results["failed"],
            "success_rate": f"{results['success_rate']:.2f}%",
            "time_taken": f"{duration:.2f}s",
            "speed": f"{(results['successful']/duration):.1f} likes/sec"
        }
    
    async def _send_batch_likes(self, video_id: str, total_likes: int) -> Dict:
        """Send likes in optimized batches"""
        BATCH_SIZE = 25  # Send 25 likes at once
        successful = 0
        failed = 0
        
        for batch_num in range(0, total_likes, BATCH_SIZE):
            batch_count = min(BATCH_SIZE, total_likes - batch_num)
            
            print(f"📦 Batch {batch_num//BATCH_SIZE + 1}: Sending {batch_count} likes...")
            
            batch_results = await self._send_single_batch(video_id, batch_count)
            successful += batch_results["successful"]
            failed += batch_results["failed"]
            
            # Small delay between batches
            if batch_num + BATCH_SIZE < total_likes:
                await asyncio.sleep(0.5)
        
        success_rate = (successful / total_likes) * 100
        
        return {
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate
        }
    
    async def _send_single_batch(self, video_id: str, count: int) -> Dict:
        """Send a single batch of likes"""
        tasks = []
        for i in range(count):
            task = self.tiktok_api.send_like(video_id)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = sum(1 for r in results if r is True)
        failed = count - successful
        
        return {"successful": successful, "failed": failed}
    
    async def bulk_send_likes(self, urls: List[str], likes_per_video: int = 200) -> List[Dict]:
        """Send likes to multiple videos"""
        results = []
        
        for url in urls:
            if self.url_handler.validate_short_url(url):
                result = await self.send_likes(url, likes_per_video)
                results.append(result)
                
                # Small delay between videos
                await asyncio.sleep(1)
            else:
                results.append({
                    "status": "error",
                    "message": "Invalid TikTok URL",
                    "url": url
                })
        
        return results
    
    def get_stats(self) -> Dict:
        """Get current statistics"""
        return {
            **self.stats,
            "uptime": time.time() - self.stats["last_activity"],
            "active_tasks": len(self.active_tasks)
        }
