// config.js
const dotenv = require('dotenv');
dotenv.config();

module.exports = {
    // Bot Info
    BOT_NAME: 'mBoT',
    BOT_AUTHOR: 'MAR-PD (MASTER)',
    BOT_VERSION: '4.0.0',
    
    // Telegram
    TELEGRAM_BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN,
    ADMIN_IDS: (process.env.ADMIN_IDS || '').split(',').map(id => parseInt(id)),
    
    // Server
    PORT: process.env.PORT || 8000,
    API_HOST: '0.0.0.0',
    
    // Security
    SESSION_SECRET: process.env.SESSION_SECRET || 'mbot-secret-key-2024',
    ENCRYPTION_KEY: process.env.ENCRYPTION_KEY || 'mbot-encryption-key-32-chars-long!!!',
    
    // TikTok Settings
    MIN_DELAY: 30,
    MAX_DELAY: 90,
    MAX_ACTIONS_PER_DAY: 50,
    COOLDOWN_MINUTES: 120,
    SAFE_HOURS_START: 0,
    SAFE_HOURS_END: 6,
    
    // Mass Report Settings
    MASS_REPORT_COUNT: 100,
    MASS_REPORT_DELAY: 60,
    
    // Report Reasons
    REPORT_REASONS: {
        violent_acts: { name: '⚠️ Violent Acts', priority: 1 },
        spam: { name: '📢 Spam', priority: 2 },
        harassment: { name: '💢 Harassment', priority: 1 },
        hate_speech: { name: '🗣️ Hate Speech', priority: 1 },
        dangerous_acts: { name: '💀 Dangerous Acts', priority: 1 },
        misinformation: { name: '📰 Misinformation', priority: 2 },
        intellectual_property: { name: '©️ IP Violation', priority: 3 }
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
• আমাদের বট দিয়ে ভিডিও পোস্ট করলে ভিডিও রিমুভ হয়ে যাইতে পারে
• অ্যাকাউন্ট ব্যান হয়ে যাওয়ার সম্ভাবনাও আছে 😩😅

✅ *সবাই ভালো থাকবেন | ভালো কাজে ইউজ করবেন*

🤲 *আল্লাহ হাফেজ* 🌺`
};
