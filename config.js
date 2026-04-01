// config.js
const dotenv = require('dotenv');
dotenv.config();

module.exports = {
    // Bot Identity
    BOT_NAME: 'mBoT',
    BOT_AUTHOR: 'MAR-PD (MASTER)',
    BOT_VERSION: '6.0.0',
    
    // Telegram
    TELEGRAM_BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN,
    ADMIN_IDS: (process.env.ADMIN_IDS || '').split(',').map(id => parseInt(id)),
    
    // Server
    PORT: process.env.PORT || 8000,
    API_HOST: '0.0.0.0',
    
    // Security
    ENCRYPTION_KEY: process.env.ENCRYPTION_KEY || 'mbot-ultimate-powerful-key-2024-32char!!!',
    
    // ============ ULTRA POWERFUL SETTINGS ============
    
    // Mass Report Settings
    MASS_REPORT_COUNT: 1000,          // Max reports per mass attack
    MASS_REPORT_DELAY: 20,            // Seconds between reports
    CONCURRENT_REPORTS: 10,           // Parallel reports (ULTRA POWERFUL!)
    
    // Account Settings
    MAX_ACTIONS_PER_DAY: 200,          // Maximum per account per day
    COOLDOWN_MINUTES: 30,              // Cooldown between actions
    SAFE_HOURS_START: 0,
    SAFE_HOURS_END: 6,
    
    // Retry Settings
    MAX_RETRIES: 5,
    RETRY_DELAY: 5,                    // Seconds between retries
    
    // Report Reasons (Multiple reasons for stronger impact)
    REPORT_REASONS: {
        violent_acts: { name: '💀 Violent Acts', priority: 1, code: 'violent' },
        dangerous_acts: { name: '⚠️ Dangerous Acts', priority: 1, code: 'dangerous' },
        harassment: { name: '💢 Harassment & Bullying', priority: 1, code: 'harassment' },
        hate_speech: { name: '🗣️ Hate Speech', priority: 1, code: 'hate' },
        spam: { name: '📢 Spam', priority: 2, code: 'spam' },
        misinformation: { name: '📰 Misinformation', priority: 2, code: 'misinfo' },
        intellectual_property: { name: '©️ Copyright Infringement', priority: 3, code: 'copyright' },
        self_harm: { name: '💔 Self Harm', priority: 1, code: 'selfharm' },
        nudity: { name: '🔞 Nudity', priority: 1, code: 'nudity' }
    },
    
    // Disclaimer
    DISCLAIMER: `⚠️ *প্রাণপ্রিয় ইউজার বন্ধুরা* ⚠️

আমাদের বটটা ভালো উদ্দেশ্যে বানানো হয়েছে, ভালো কাজের জন্য বানানো হয়েছে। 
তারপরেও অনিচ্ছাকৃতভাবে কিছুটা TikTok এর আইন নষ্ট করতেছে, এটা ব্যাপার না।

❌ *কঠোর নিষেধাজ্ঞা:*
• কেউ খারাপ কাজে আমাদের বট ইউজ করবেন না
• অন্যের ক্ষতি করার চেষ্টা করবেন না
• যদি কোন খারাপ কাজ দেখি — আমরা বট অফ করে দিব বা ব্যান করে দেব

⚠️ *সতর্কতা:*
• আমাদের বট দিয়ে ভিডিও রিপোর্ট করলে ভিডিও রিমুভ হয়ে যাইতে পারে
• অ্যাকাউন্ট ব্যান হয়ে যাওয়ার সম্ভাবনাও আছে 😩😅

✅ *সবাই ভালো থাকবেন | ভালো কাজে ইউজ করবেন*

🤲 *আল্লাহ হাফেজ* 🌺`
};
