// core.js
const { chromium } = require('playwright');
const crypto = require('crypto');

class TikTokReporter {
    constructor(account, proxy = null) {
        this.account = account;
        this.proxy = proxy;
        this.browser = null;
        this.page = null;
    }
    
    async report(targetUrl, reason = 'violent') {
        let success = false;
        let errorMsg = null;
        
        try {
            // ব্রাউজার লঞ্চ
            const proxyConfig = this.proxy ? {
                server: `http://${this.proxy}`
            } : null;
            
            this.browser = await chromium.launch({
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ],
                proxy: proxyConfig
            });
            
            const context = await this.browser.newContext({
                viewport: { width: 390, height: 844 },
                userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
            });
            
            this.page = await context.newPage();
            
            // লগইন
            await this.page.goto('https://www.tiktok.com/login/phone-or-email');
            await this.sleep(3000, 5000);
            
            await this.page.fill('input[placeholder="Email or username"]', this.account.email);
            await this.sleep(1000, 1500);
            await this.page.fill('input[type="password"]', this.account.password);
            await this.sleep(1000, 1500);
            await this.page.click('button[type="submit"]');
            await this.sleep(5000, 7000);
            
            // রিপোর্ট
            await this.page.goto(targetUrl);
            await this.sleep(4000, 6000);
            
            // মোর অ্যাকশন
            try {
                await this.page.click('button[aria-label="More actions"]', { timeout: 5000 });
                await this.sleep(1000, 2000);
            } catch(e) {
                // বিকল্প সিলেক্টর
                await this.page.click('div[data-e2e="more-actions"]', { timeout: 5000 });
                await this.sleep(1000, 2000);
            }
            
            // রিপোর্ট বাটন
            await this.page.click('button:has-text("Report"), div:has-text("Report")', { timeout: 5000 });
            await this.sleep(1500, 2000);
            
            // কারণ সিলেক্ট
            const reasonText = {
                violent: 'Violent acts',
                spam: 'Spam',
                harassment: 'Harassment',
                hate_speech: 'Hate speech'
            }[reason] || 'Violent acts';
            
            await this.page.click(`div:has-text("${reasonText}"), span:has-text("${reasonText}")`, { timeout: 5000 });
            await this.sleep(1000, 1500);
            
            // সাবমিট
            await this.page.click('button:has-text("Submit"), button:has-text("Report")', { timeout: 5000 });
            await this.sleep(2000, 3000);
            
            success = true;
            console.log(`✓ ${this.account.email} - রিপোর্ট সফল`);
            
        } catch(e) {
            errorMsg = e.message;
            console.log(`✗ ${this.account.email} - ব্যর্থ: ${e.message}`);
        } finally {
            if (this.browser) await this.browser.close();
        }
        
        return { success, error: errorMsg };
    }
    
    sleep(min, max) {
        const delay = min + Math.random() * (max - min);
        return new Promise(resolve => setTimeout(resolve, delay));
    }
}

module.exports = TikTokReporter;
