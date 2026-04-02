// config.js
require('dotenv').config();

module.exports = {
    BOT_NAME: 'mBoT',
    BOT_AUTHOR: 'MAR-PD',
    
    TELEGRAM_BOT_TOKEN: process.env.TELEGRAM_BOT_TOKEN,
    ADMIN_IDS: (process.env.ADMIN_IDS || '').split(',').map(id => parseInt(id)),
    
    PORT: process.env.PORT || 8000,
    
    // ফ্রি প্রক্সি API সোর্স (সব ফ্রি)
    FREE_PROXY_APIS: [
        'https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all',
        'https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt',
        'https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt',
        'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt',
        'https://www.proxy-list.download/api/v1/get?type=http',
        'https://api.openproxylist.xyz/http.txt',
        'https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt',
        'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt'
    ],
    
    PROXY_REFRESH_INTERVAL: 30, // মিনিটে একবার নতুন প্রক্সি আনবে
    MAX_PROXIES: 500,
    
    // রিপোর্ট সেটিংস
    MASS_REPORT_DELAY: 25, // সেকেন্ড
    MAX_REPORTS_PER_ACCOUNT: 50,
    
    REPORT_REASONS: {
        violent: 'Violent acts',
        spam: 'Spam',
        harassment: 'Harassment',
        hate_speech: 'Hate speech'
    },
    
    DISCLAIMER: `⚠️ সতর্কতা: এই বট শুধুমাত্র স্প্যাম ও ক্ষতিকর কন্টেন্ট রিপোর্ট করার জন্য।`
};
