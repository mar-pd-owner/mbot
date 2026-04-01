// server.js
const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const config = require('./config');
const logger = require('./logger');
const AccountManager = require('./account-manager');
const URLExtractor = require('./url-extractor');
const TikTokAutomation = require('./core');

const app = express();
const accountManager = new AccountManager();

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 200,
    message: { error: 'Too many requests, please try again later.' }
});
app.use('/api/', limiter);

// ============ HEALTH CHECK ============
app.get('/health', (req, res) => {
    res.json({ 
        status: 'online', 
        bot: config.BOT_NAME,
        version: config.BOT_VERSION,
        author: config.BOT_AUTHOR,
        timestamp: new Date().toISOString()
    });
});

// ============ API ENDPOINTS ============

// Get bot stats
app.get('/api/stats', (req, res) => {
    res.json(accountManager.getStats());
});

// Extract TikTok URL
app.post('/api/extract-url', async (req, res) => {
    const { url } = req.body;
    if (!url) return res.status(400).json({ error: 'URL is required' });
    const result = await URLExtractor.extractTikTokUrl(url);
    res.json(result);
});

// Add account (from API)
app.post('/api/account/add', (req, res) => {
    const { email, password } = req.body;
    if (!email || !password) {
        return res.status(400).json({ error: 'Email and password required' });
    }
    const account = accountManager.addAccount(email, password);
    res.json({ success: true, account });
});

// Add multiple accounts
app.post('/api/account/add-bulk', (req, res) => {
    const { accounts } = req.body;
    if (!accounts || !Array.isArray(accounts)) {
        return res.status(400).json({ error: 'Accounts array required' });
    }
    const results = accountManager.addAccountsBulk(accounts);
    res.json({ success: true, added: results.length, accounts: results });
});

// Remove account
app.delete('/api/account/:id', (req, res) => {
    const result = accountManager.removeAccount(req.params.id);
    res.json(result);
});

// Get all accounts
app.get('/api/accounts', (req, res) => {
    res.json({ accounts: accountManager.getAllAccounts(), total: accountManager.accounts.length });
});

// Update account status
app.put('/api/account/:id/status', (req, res) => {
    const { status } = req.body;
    const result = accountManager.updateAccountStatus(req.params.id, status);
    res.json({ success: result });
});

// Single report
app.post('/api/report', async (req, res) => {
    const { url, reason = 'violent_acts', account_id = null } = req.body;
    
    if (!url) return res.status(400).json({ error: 'URL is required' });
    
    // Extract URL
    let videoUrl = url;
    if (URLExtractor.isValidShortUrl(url)) {
        const extracted = await URLExtractor.extractTikTokUrl(url);
        if (!extracted.success) {
            return res.status(400).json({ error: 'Failed to extract URL', details: extracted.error });
        }
        videoUrl = extracted.fullUrl;
    }
    
    // Get account
    let account;
    if (account_id) {
        account = accountManager.getAccount(account_id);
    } else {
        const accounts = accountManager.getAvailableAccounts(1);
        account = accounts[0] || null;
    }
    
    if (!account) {
        return res.status(503).json({ error: 'No available accounts' });
    }
    
    const proxy = accountManager.getRandomProxy();
    const automation = new TikTokAutomation(account, proxy);
    
    try {
        const initialized = await automation.init();
        if (!initialized) throw new Error('Failed to initialize browser');
        
        const loggedIn = await automation.login();
        if (!loggedIn) {
            accountManager.updateAccountUsage(account.id, false);
            throw new Error('Login failed');
        }
        
        const result = await automation.reportVideo(videoUrl, reason);
        accountManager.updateAccountUsage(account.id, result.success);
        
        if (result.success) {
            accountManager.addReportRecord(videoUrl, 1, 1, reason);
        }
        
        res.json({
            success: result.success,
            account: account.email,
            video_url: videoUrl,
            reason: reason,
            result: result
        });
        
    } catch (error) {
        accountManager.updateAccountUsage(account.id, false);
        res.status(500).json({ error: error.message });
    } finally {
        await automation.close();
    }
});

// MASS REPORT - ULTRA POWERFUL
app.post('/api/mass-report', async (req, res) => {
    const { url, count = config.MASS_REPORT_COUNT, reason = 'violent_acts' } = req.body;
    
    if (!url) return res.status(400).json({ error: 'URL is required' });
    
    // Extract URL
    let videoUrl = url;
    if (URLExtractor.isValidShortUrl(url)) {
        const extracted = await URLExtractor.extractTikTokUrl(url);
        if (!extracted.success) {
            return res.status(400).json({ error: 'Failed to extract URL', details: extracted.error });
        }
        videoUrl = extracted.fullUrl;
    }
    
    // Get available accounts
    const accounts = accountManager.getAvailableAccounts(Math.min(count, 500));
    
    if (accounts.length === 0) {
        return res.status(503).json({ error: 'No available accounts' });
    }
    
    const results = [];
    let successCount = 0;
    const totalToUse = Math.min(accounts.length, count);
    
    for (let i = 0; i < totalToUse; i++) {
        const account = accounts[i];
        const proxy = accountManager.getRandomProxy();
        const automation = new TikTokAutomation(account, proxy);
        
        try {
            const initialized = await automation.init();
            if (!initialized) {
                results.push({ account: account.email, success: false, error: 'Init failed' });
                accountManager.updateAccountUsage(account.id, false);
                continue;
            }
            
            const loggedIn = await automation.login();
            if (!loggedIn) {
                results.push({ account: account.email, success: false, error: 'Login failed' });
                accountManager.updateAccountUsage(account.id, false);
                continue;
            }
            
            const result = await automation.reportVideo(videoUrl, reason);
            
            if (result.success) {
                successCount++;
                results.push({ account: account.email, success: true });
            } else {
                results.push({ account: account.email, success: false, error: result.error });
            }
            
            accountManager.updateAccountUsage(account.id, result.success);
            
            // Delay between reports
            await new Promise(resolve => setTimeout(resolve, config.MASS_REPORT_DELAY * 1000));
            
        } catch (error) {
            results.push({ account: account.email, success: false, error: error.message });
            accountManager.updateAccountUsage(account.id, false);
        } finally {
            await automation.close();
        }
        
        // Log progress every 10 reports
        if ((i + 1) % 10 === 0) {
            logger.info(`📊 Mass report progress: ${i + 1}/${totalToUse}, success: ${successCount}`);
        }
    }
    
    // Save report record
    accountManager.addReportRecord(videoUrl, successCount, totalToUse, reason);
    
    res.json({
        success: successCount > 0,
        video_url: videoUrl,
        reason: reason,
        total_requested: Math.min(accounts.length, count),
        total_executed: results.length,
        successful: successCount,
        failed: results.length - successCount,
        success_rate: ((successCount / results.length) * 100).toFixed(1),
        results: results.slice(0, 20) // Return first 20 results
    });
});

// Reset daily counters
app.post('/api/admin/reset', (req, res) => {
    accountManager.resetDailyCounters();
    res.json({ success: true, message: 'Daily counters reset' });
});

// Get report history
app.get('/api/reports', (req, res) => {
    const limit = parseInt(req.query.limit) || 20;
    res.json({ reports: accountManager.getRecentReports(limit) });
});

// Start server
app.listen(config.PORT, config.API_HOST, () => {
    logger.info(`🚀 ${config.BOT_NAME} API Server running on port ${config.PORT}`);
    logger.info(`📊 Stats: ${JSON.stringify(accountManager.getStats())}`);
});

module.exports = app;
