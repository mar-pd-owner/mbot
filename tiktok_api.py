"""
TikTok Web Automation - Zefoy-like Method
Uses browser automation to mimic real user
"""

import asyncio
import random
import time
from typing import Dict
import re

# Optional: Use selenium for browser automation
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.action_chains import ActionChains
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("⚠️ Selenium not installed. Install: pip install selenium")

class TikTokWebAPI:
    def __init__(self, config: Dict):
        self.config = config
        self.driver = None
        self.is_logged_in = False
        
    async def init_browser(self):
        """Initialize browser for automation"""
        if not SELENIUM_AVAILABLE:
            return False
            
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            return True
        except Exception as e:
            print(f"❌ Browser init error: {e}")
            return False
    
    async def send_like_via_web(self, video_url: str) -> Dict:
        """
        Send like using web automation (like real user)
        """
        if not self.driver:
            success = await self.init_browser()
            if not success:
                return {'success': False, 'message': 'Browser init failed'}
        
        try:
            # Navigate to video
            print(f"🌐 Opening: {video_url}")
            self.driver.get(video_url)
            await asyncio.sleep(3)  # Wait for page load
            
            # Try to find like button
            like_button = None
            
            # Multiple selectors for like button
            selectors = [
                'button[data-e2e="like-icon"]',
                'div[aria-label="Like"]',
                'svg[aria-label="Like"]',
                'button[class*="like"]',
                'div[class*="like"]'
            ]
            
            for selector in selectors:
                try:
                    like_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if like_button:
                        break
                except:
                    continue
            
            if not like_button:
                # Take screenshot for debugging
                self.driver.save_screenshot("tiktok_error.png")
                return {'success': False, 'message': 'Like button not found'}
            
            # Click like button
            print("🎯 Clicking like button...")
            like_button.click()
            await asyncio.sleep(2)
            
            # Check if liked successfully
            # Look for "Liked" text or filled heart
            page_source = self.driver.page_source
            liked_indicators = ['liked', 'Liked', 'aria-pressed="true"', 'filled="true"']
            
            for indicator in liked_indicators:
                if indicator in page_source:
                    return {'success': True, 'message': 'Like sent via web'}
            
            return {'success': False, 'message': 'Like may not have registered'}
            
        except Exception as e:
            return {'success': False, 'message': f'Web automation error: {str(e)}'}
    
    async def close(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
