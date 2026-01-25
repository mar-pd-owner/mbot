"""
MBOT Core Engine - Fixed Version
"""

import asyncio
import time
import random
import hashlib
from typing import Dict, List
from tiktok_api import TikTokAPI

class MBotCore:
    def __init__(self, config: Dict):
        self.config = config
        self.api = TikTokAPI(config)
        self.stats = {
            "total_likes_sent": 0,
            "total_videos": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "start_time": time.time()
        }
    
    async def send_likes(self, video_id: str, like_count: int = 100) -> Dict:
        """
        Send likes to TikTok video
        """
        print(f"\n🎯 Processing Video ID: {video_id}")
        print(f"🎯 Target Likes: {like_count}")
        print("-" * 40)
        
        successful = 0
        failed = 0
        start_time = time.time()
        
        try:
            # Send likes in batches
            batch_size = self.config['tiktok']['batch_size']
            
            for batch_num in range(0, like_count, batch_size):
                current_batch = min(batch_size, like_count - batch_num)
                print(f"📦 Batch {batch_num//batch_size + 1}: Sending {current_batch} likes...")
                
                # Create tasks for this batch
                tasks = []
                for _ in range(current_batch):
                    task = self.api.send_like(video_id)
                    tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        failed += 1
                        print(f"  ❌ Error: {str(result)[:50]}")
                    elif isinstance(result, dict):
                        if result.get('success'):
                            successful += 1
                            print("  ✅ Success")
                        else:
                            failed += 1
                            print(f"  ❌ Failed: {result.get('message', 'Unknown')[:50]}")
                
                # Small delay between batches
                if batch_num + batch_size < like_count:
                    await asyncio.sleep(0.5)
            
            # Calculate statistics
            end_time = time.time()
            duration = end_time - start_time
            
            # Update stats
            self.stats["total_likes_sent"] += successful
            self.stats["total_videos"] += 1
            self.stats["successful_requests"] += successful
            self.stats["failed_requests"] += failed
            
            success_rate = (successful / like_count) * 100 if like_count > 0 else 0
            
            result = {
                "status": "success" if successful > 0 else "failed",
                "video_id": video_id,
                "requested_likes": like_count,
                "sent_likes": successful,
                "failed_likes": failed,
                "success_rate": f"{success_rate:.1f}%",
                "time_taken": f"{duration:.2f}s",
                "speed": f"{(successful/duration):.1f} likes/sec" if duration > 0 else "0",
                "timestamp": time.strftime('%H:%M:%S')
            }
            
            print("\n" + "-" * 40)
            print("📊 RESULTS:")
            print(f"✅ Successful: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"📈 Success Rate: {success_rate:.1f}%")
            print(f"⏱️ Time: {duration:.2f}s")
            print(f"⚡ Speed: {(successful/duration):.1f} likes/sec")
            
            return result
            
        except Exception as e:
            print(f"\n❌ Error in send_likes: {e}")
            return {
                "status": "error",
                "message": str(e),
                "sent_likes": successful,
                "failed_likes": failed
            }
    
    def get_stats(self) -> Dict:
        """Get bot statistics"""
        total_requests = self.stats["successful_requests"] + self.stats["failed_requests"]
        overall_success_rate = (self.stats["successful_requests"] / total_requests * 100) if total_requests > 0 else 0
        
        uptime_seconds = time.time() - self.stats["start_time"]
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        return {
            "total_likes_sent": self.stats["total_likes_sent"],
            "total_videos": self.stats["total_videos"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "overall_success_rate": f"{overall_success_rate:.1f}%",
            "uptime": f"{hours}h {minutes}m {seconds}s",
            "avg_likes_per_video": self.stats["total_likes_sent"] / self.stats["total_videos"] if self.stats["total_videos"] > 0 else 0,
            "bot_status": "🟢 Online"
        }
