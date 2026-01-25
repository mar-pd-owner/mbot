"""
MBOT Core Engine - Updated with Better Error Handling
"""

import asyncio
import time
import random
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
            "start_time": time.time(),
            "last_success": 0
        }
        
        # Test API connection on startup
        asyncio.create_task(self.test_api())
    
    async def test_api(self):
        """Test API connection"""
        print("🔍 Testing TikTok API connection...")
        is_working = await self.api.test_connection()
        if is_working:
            print("✅ TikTok API connection successful")
        else:
            print("⚠️ TikTok API connection may have issues")
    
    async def send_likes(self, video_id: str, like_count: int = 100) -> Dict:
        """
        Send likes to TikTok video with improved error handling
        """
        print(f"\n🎯 Processing Video ID: {video_id}")
        print(f"🎯 Target Likes: {like_count}")
        print("-" * 40)
        
        successful = 0
        failed = 0
        start_time = time.time()
        
        # Validate video ID
        if len(video_id) < 5:
            return {
                "status": "error",
                "message": f"Invalid video ID: {video_id}",
                "sent_likes": 0,
                "failed_likes": like_count
            }
        
        try:
            # Send likes in smaller batches for better success rate
            batch_size = 5  # Smaller batch size
            max_retries = 2  # Retry failed requests
            
            for batch_num in range(0, like_count, batch_size):
                current_batch = min(batch_size, like_count - batch_num)
                print(f"📦 Batch {batch_num//batch_size + 1}: Sending {current_batch} likes...")
                
                # Create tasks with retry logic
                tasks = []
                for i in range(current_batch):
                    task = self.send_like_with_retry(video_id, max_retries)
                    tasks.append(task)
                
                # Execute batch
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for result in batch_results:
                    if isinstance(result, Exception):
                        failed += 1
                        print(f"  ❌ Exception: {str(result)[:50]}")
                    elif isinstance(result, dict):
                        if result.get('success'):
                            successful += 1
                            print("  ✅ Success")
                            self.stats["last_success"] = time.time()
                        else:
                            failed += 1
                            error_msg = result.get('message', 'Unknown error')
                            print(f"  ❌ Failed: {error_msg[:50]}")
                
                # Dynamic delay based on success rate
                if successful > 0:
                    # If we're having success, go faster
                    delay = random.uniform(0.2, 0.5)
                else:
                    # If failing, slow down
                    delay = random.uniform(0.5, 1.0)
                
                if batch_num + batch_size < like_count:
                    await asyncio.sleep(delay)
            
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
                "status": "success" if successful > 0 else "partial" if successful > 0 else "failed",
                "video_id": video_id,
                "requested_likes": like_count,
                "sent_likes": successful,
                "failed_likes": failed,
                "success_rate": f"{success_rate:.1f}%",
                "time_taken": f"{duration:.2f}s",
                "speed": f"{(successful/duration):.1f} likes/sec" if duration > 0 else "0",
                "timestamp": time.strftime('%H:%M:%S'),
                "message": f"Sent {successful} of {like_count} likes"
            }
            
            print("\n" + "-" * 40)
            print("📊 RESULTS:")
            print(f"✅ Successful: {successful}")
            print(f"❌ Failed: {failed}")
            print(f"📈 Success Rate: {success_rate:.1f}%")
            print(f"⏱️ Time: {duration:.2f}s")
            if successful > 0 and duration > 0:
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
    
    async def send_like_with_retry(self, video_id: str, max_retries: int = 2) -> Dict:
        """Send like with retry logic"""
        for attempt in range(max_retries + 1):
            try:
                result = await self.api.send_like(video_id)
                
                # If success, return immediately
                if result.get('success'):
                    return result
                
                # If last attempt, return failure
                if attempt == max_retries:
                    return result
                
                # Wait before retry
                await asyncio.sleep(random.uniform(0.5, 1.0))
                
            except Exception as e:
                if attempt == max_retries:
                    return {'success': False, 'message': f'Exception: {str(e)}'}
                await asyncio.sleep(random.uniform(0.5, 1.0))
        
        return {'success': False, 'message': 'Max retries exceeded'}
    
    def get_stats(self) -> Dict:
        """Get bot statistics"""
        total_requests = self.stats["successful_requests"] + self.stats["failed_requests"]
        overall_success_rate = (self.stats["successful_requests"] / total_requests * 100) if total_requests > 0 else 0
        
        uptime_seconds = time.time() - self.stats["start_time"]
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        # Calculate time since last success
        time_since_last = time.time() - self.stats["last_success"]
        if self.stats["last_success"] == 0:
            last_success_str = "Never"
        elif time_since_last < 60:
            last_success_str = f"{int(time_since_last)} seconds ago"
        elif time_since_last < 3600:
            last_success_str = f"{int(time_since_last/60)} minutes ago"
        else:
            last_success_str = f"{int(time_since_last/3600)} hours ago"
        
        return {
            "total_likes_sent": self.stats["total_likes_sent"],
            "total_videos": self.stats["total_videos"],
            "successful_requests": self.stats["successful_requests"],
            "failed_requests": self.stats["failed_requests"],
            "overall_success_rate": f"{overall_success_rate:.1f}%",
            "uptime": f"{hours}h {minutes}m {seconds}s",
            "last_success": last_success_str,
            "avg_likes_per_video": self.stats["total_likes_sent"] / self.stats["total_videos"] if self.stats["total_videos"] > 0 else 0,
            "bot_status": "🟢 Online" if self.stats["last_success"] > time.time() - 300 else "🟡 Idle" if self.stats["last_success"] > 0 else "🔴 No success"
        }
