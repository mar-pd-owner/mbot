// core.js
const { chromium } = require('playwright');
const logger = require('./logger');
const config = require('./config');

class TikTokAutomation {
    constructor(account, proxy = null) {
        this.account = account;
        this.proxy = proxy;
        this.browser = null;
        this.context = null;
        this.page = null;
        this.sessionId = `${account.email}_${Date.now()}`;
    }
    
    async init() {
        try {
            const userAgents = [
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Mobile/15E148 Safari/604.1',
                'Mozilla/5.0 (Linux; Android 13; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
                'Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
            ];
            
            const browserArgs = [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security',
                '--disable-automation',
                '--disable-extensions',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-accelerated-2d-canvas',
                '--disable-component-extensions-with-background-pages',
                '--disable-default-apps',
                '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                '--disable-infobars',
                '--disable-notifications',
                '--disable-popup-blocking',
                '--disable-sync',
                '--hide-scrollbars',
                '--ignore-certificate-errors',
                '--mute-audio'
            ];
            
            const proxyConfig = this.proxy ? {
                server: `http://${this.proxy.server}:${this.proxy.port}`,
                username: this.proxy.username,
                password: this.proxy.password
            } : null;
            
            this.browser = await chromium.launch({
                headless: true,
                args: browserArgs,
                proxy: proxyConfig
            });
            
            this.context = await this.browser.newContext({
                userAgent: userAgents[Math.floor(Math.random() * userAgents.length)],
                viewport: { width: 390, height: 844 },
                locale: 'en-US',
                hasTouch: true,
                isMobile: true,
                deviceScaleFactor: 3,
                timezoneId: 'America/New_York',
                permissions: ['geolocation'],
                extraHTTPHeaders: {
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none'
                }
            });
            
            // Anti-detection script
            await this.context.addInitScript(`
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'platform', { get: () => 'iPhone' });
                Object.defineProperty(navigator, 'vendor', { get: () => 'Apple Computer, Inc.' });
                
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            `);
            
            this.page = await this.context.newPage();
            logger.info(`🌐 Browser initialized for ${this.account.email}`);
            return true;
            
        } catch (error) {
            logger.error(`❌ Init failed for ${this.account.email}: ${error.message}`);
            return false;
        }
    }
    
    async login() {
        try {
            await this.page.goto('https://www.tiktok.com/login/phone-or-email', {
                waitUntil: 'networkidle',
                timeout: 30000
            });
            
            await this._randomDelay(2000, 4000);
            
            // Try multiple selectors for email input
            const emailSelectors = [
                'input[placeholder="Email or username"]',
                'input[name="username"]',
                'input[type="text"]'
            ];
            
            let emailInput = null;
            for (const selector of emailSelectors) {
                emailInput = await this.page.waitForSelector(selector, { timeout: 5000 }).catch(() => null);
                if (emailInput) break;
            }
            
            if (!emailInput) {
                throw new Error('Email input not found');
            }
            
            await this._humanType(emailInput, this.account.email);
            await this._randomDelay(500, 1000);
            
            // Password input
            const passwordInput = await this.page.waitForSelector('input[type="password"]', { timeout: 10000 });
            await this._humanType(passwordInput, this.account.password);
            await this._randomDelay(500, 1000);
            
            // Submit
            await this.page.click('button[type="submit"]');
            await this._randomDelay(5000, 8000);
            
            // Check success
            const currentUrl = this.page.url();
            if (currentUrl.includes('feed') || currentUrl.includes('foryou') || currentUrl.includes('user')) {
                logger.info(`✅ Login success: ${this.account.email}`);
                return true;
            }
            
            // Check for captcha
            const hasCaptcha = await this.page.isVisible('iframe[title*="captcha"], div[class*="captcha"]').catch(() => false);
            if (hasCaptcha) {
                logger.warn(`⚠️ Captcha detected for ${this.account.email}`);
                return false;
            }
            
            logger.error(`❌ Login failed for ${this.account.email}`);
            return false;
            
        } catch (error) {
            logger.error(`❌ Login error for ${this.account.email}: ${error.message}`);
            return false;
        }
    }
    
    async reportVideo(videoUrl, reason = 'violent_acts') {
        try {
            await this.page.goto(videoUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
            await this._randomDelay(3000, 5000);
            
            // Try multiple selectors for more actions button
            const moreSelectors = [
                'button[aria-label="More actions"]',
                'div[data-e2e="more-actions"]',
                'button[class*="more"]',
                'div[class*="share"]'
            ];
            
            let moreBtn = null;
            for (const selector of moreSelectors) {
                moreBtn = await this.page.waitForSelector(selector, { timeout: 3000 }).catch(() => null);
                if (moreBtn) break;
            }
            
            if (moreBtn) {
                await moreBtn.click();
                await this._randomDelay(1500, 2500);
            }
            
            // Report button
            const reportSelectors = [
                'button:has-text("Report")',
                'div:has-text("Report")',
                'span:has-text("Report")',
                'button[class*="report"]'
            ];
            
            let reportBtn = null;
            for (const selector of reportSelectors) {
                reportBtn = await this.page.waitForSelector(selector, { timeout: 3000 }).catch(() => null);
                if (reportBtn) break;
            }
            
            if (!reportBtn) {
                throw new Error('Report button not found');
            }
            
            await reportBtn.click();
            await this._randomDelay(1500, 2500);
            
            // Select reason
            const reasonMap = {
                violent_acts: ['Violent acts', 'Violence', 'Violent'],
                dangerous_acts: ['Dangerous acts', 'Dangerous'],
                harassment: ['Harassment', 'Bullying'],
                hate_speech: ['Hate speech', 'Hate'],
                spam: ['Spam'],
                self_harm: ['Self harm', 'Self-harm'],
                nudity: ['Nudity', 'Sexual content']
            };
            
            const reasonTexts = reasonMap[reason] || reasonMap.violent_acts;
            let reasonSelected = false;
            
            for (const text of reasonTexts) {
                const reasonSelectors = [
                    `div:has-text("${text}")`,
                    `span:has-text("${text}")`,
                    `button:has-text("${text}")`
                ];
                
                for (const selector of reasonSelectors) {
                    const reasonBtn = await this.page.waitForSelector(selector, { timeout: 2000 }).catch(() => null);
                    if (reasonBtn) {
                        await reasonBtn.click();
                        reasonSelected = true;
                        await this._randomDelay(1000, 1500);
                        break;
                    }
                }
                if (reasonSelected) break;
            }
            
            if (!reasonSelected) {
                throw new Error('Reason not found');
            }
            
            // Submit
            const submitSelectors = [
                'button:has-text("Submit")',
                'button:has-text("Report")',
                'button[type="submit"]'
            ];
            
            let submitBtn = null;
            for (const selector of submitSelectors) {
                submitBtn = await this.page.waitForSelector(selector, { timeout: 3000 }).catch(() => null);
                if (submitBtn) break;
            }
            
            if (submitBtn) {
                await submitBtn.click();
                await this._randomDelay(2500, 3500);
                logger.info(`✅ Report submitted for ${videoUrl} using ${this.account.email}`);
                return { success: true, reason };
            }
            
            throw new Error('Submit button not found');
            
        } catch (error) {
            logger.error(`❌ Report failed for ${this.account.email}: ${error.message}`);
            return { success: false, error: error.message };
        }
    }
    
    async _humanType(element, text) {
        for (const char of text) {
            await element.type(char, { delay: Math.random() * 80 + 40 });
        }
    }
    
    async _randomDelay(min, max) {
        const delay = Math.random() * (max - min) + min;
        await new Promise(resolve => setTimeout(resolve, delay));
    }
    
    async close() {
        if (this.browser) {
            await this.browser.close();
            logger.info(`🔒 Browser closed for ${this.account.email}`);
        }
    }
}

module.exports = TikTokAutomation;
