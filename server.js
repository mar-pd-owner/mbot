// server.js
const express = require('express');
const cors = require('cors');
const fs = require('fs');
const config = require('./config');
const FreeProxyManager = require('./proxy-manager');
const TikTokReporter = require('./core');

const app = express();
app.use(cors());
app.use(express.json());

const proxyManager = new FreeProxyManager();

// হেলথ চেক
app.get('/health', (req, res) => {
    res.json({ status: 'online', time: new Date().toISOString() });
});

// স্ট্যাটাস
app.get('/api/stats', (req, res) => {
    let accounts = [];
    try {
        accounts = JSON.parse(fs.readFileSync('./data/accounts.json', 'utf8'));
    } catch(e) {}
    
    res.json({
        total_accounts: accounts.length,
        active_proxies: proxyManager.proxies.length,
        last_proxy_update: proxyManager.lastUpdate,
        bot: config.BOT_NAME
    });
});

// একক রিপোর্ট
app.post('/api/report', async (req, res) => {
    const { url, reason } = req.body;
    
    if (!url) {
        return res.status(400).json({ error: 'URL required' });
    }
    
    // অ্যাকাউন্ট লোড
    let accounts = [];
    try {
        accounts = JSON.parse(fs.readFileSync('./data/accounts.json', 'utf8'));
    } catch(e) {
        return res.status(500).json({ error: 'No accounts found' });
    }
    
    const activeAccounts = accounts.filter(a => a.status !== 'banned');
    if (activeAccounts.length === 0) {
        return res.status(503).json({ error: 'No active accounts' });
    }
    
    // প্রক্সি রিফ্রেশ
    await proxyManager.refreshIfNeeded();
    
    // রিপোর্ট এক্সিকিউট
    const account = activeAccounts[0];
    const proxy = proxyManager.getRandomProxy();
    const reporter = new TikTokReporter(account, proxy);
    
    const result = await reporter.report(url, reason || 'violent');
    
    // অ্যাকাউন্ট আপডেট
    if (result.success) {
        account.used_today = (account.used_today || 0) + 1;
        account.last_used = new Date().toISOString();
        fs.writeFileSync('./data/accounts.json', JSON.stringify(accounts, null, 2));
    }
    
    res.json({
        success: result.success,
        account: account.email,
        error: result.error
    });
});

// ম্যাস রিপোর্ট
app.post('/api/mass-report', async (req, res) => {
    const { url, count = 100, reason } = req.body;
    
    if (!url) {
        return res.status(400).json({ error: 'URL required' });
    }
    
    // অ্যাকাউন্ট লোড
    let accounts = [];
    try {
        accounts = JSON.parse(fs.readFileSync('./data/accounts.json', 'utf8'));
    } catch(e) {
        return res.status(500).json({ error: 'No accounts found' });
    }
    
    const activeAccounts = accounts.filter(a => a.status !== 'banned' && (a.used_today || 0) < 50);
    const useCount = Math.min(activeAccounts.length, count);
    
    if (useCount === 0) {
        return res.status(503).json({ error: 'No available accounts' });
    }
    
    // প্রক্সি রিফ্রেশ
    await proxyManager.refreshIfNeeded();
    
    const results = [];
    let successCount = 0;
    
    for (let i = 0; i < useCount; i++) {
        const account = activeAccounts[i];
        const proxy = proxyManager.getRandomProxy();
        const reporter = new TikTokReporter(account, proxy);
        
        const result = await reporter.report(url, reason || 'violent');
        
        if (result.success) {
            successCount++;
            account.used_today = (account.used_today || 0) + 1;
            account.last_used = new Date().toISOString();
        } else {
            account.fail_count = (account.fail_count || 0) + 1;
            if (account.fail_count >= 3) {
                account.status = 'suspicious';
            }
        }
        
        results.push({
            account: account.email,
            success: result.success,
            error: result.error
        });
        
        // সেভ প্রোগ্রেস
        fs.writeFileSync('./data/accounts.json', JSON.stringify(accounts, null, 2));
        
        // ডিলে
        await new Promise(r => setTimeout(r, config.MASS_REPORT_DELAY * 1000));
    }
    
    res.json({
        success: successCount > 0,
        total: useCount,
        successful: successCount,
        failed: useCount - successCount,
        success_rate: ((successCount / useCount) * 100).toFixed(1),
        results: results.slice(0, 20)
    });
});

// প্রক্সি রিফ্রেশ
app.post('/api/proxy/refresh', async (req, res) => {
    await proxyManager.fetchFreeProxies();
    res.json({ proxies: proxyManager.proxies.length });
});

app.listen(config.PORT, '0.0.0.0', () => {
    console.log(`🚀 API Server running on port ${config.PORT}`);
});

module.exports = app;
