// account-manager.js
const fs = require('fs');
const path = require('path');
const CryptoJS = require('crypto-js');
const logger = require('./logger');
const config = require('./config');

class AccountManager {
    constructor() {
        this.dataPath = path.join(__dirname, 'data');
        this.accountsFile = path.join(this.dataPath, 'accounts.json');
        this.proxiesFile = path.join(this.dataPath, 'proxies.json');
        this.settingsFile = path.join(this.dataPath, 'settings.json');
        this.reportsFile = path.join(this.dataPath, 'reports.json');
        
        this.ensureDataDirectory();
        this.loadData();
        
        // Auto-reset daily counters at midnight
        setInterval(() => this.checkAndResetDaily(), 60000);
    }
    
    ensureDataDirectory() {
        if (!fs.existsSync(this.dataPath)) {
            fs.mkdirSync(this.dataPath, { recursive: true });
        }
    }
    
    loadData() {
        // Load Accounts
        if (fs.existsSync(this.accountsFile)) {
            this.accounts = JSON.parse(fs.readFileSync(this.accountsFile, 'utf8'));
            logger.info(`📧 Loaded ${this.accounts.length} accounts`);
        } else {
            this.accounts = [];
            this.saveAccounts();
        }
        
        // Load Proxies
        if (fs.existsSync(this.proxiesFile)) {
            this.proxies = JSON.parse(fs.readFileSync(this.proxiesFile, 'utf8'));
            logger.info(`🌐 Loaded ${this.proxies.length} proxies`);
        } else {
            this.proxies = [];
            this.saveProxies();
        }
        
        // Load Settings
        if (fs.existsSync(this.settingsFile)) {
            this.settings = JSON.parse(fs.readFileSync(this.settingsFile, 'utf8'));
        } else {
            this.settings = {
                total_actions: 0,
                total_reports: 0,
                last_reset: new Date().toISOString(),
                bot_status: 'online',
                start_time: new Date().toISOString()
            };
            this.saveSettings();
        }
        
        // Load Reports History
        if (fs.existsSync(this.reportsFile)) {
            this.reports = JSON.parse(fs.readFileSync(this.reportsFile, 'utf8'));
        } else {
            this.reports = [];
            this.saveReports();
        }
    }
    
    encrypt(text) {
        return CryptoJS.AES.encrypt(text, config.ENCRYPTION_KEY).toString();
    }
    
    decrypt(encrypted) {
        try {
            const bytes = CryptoJS.AES.decrypt(encrypted, config.ENCRYPTION_KEY);
            return bytes.toString(CryptoJS.enc.Utf8);
        } catch {
            return encrypted;
        }
    }
    
    saveAccounts() {
        fs.writeFileSync(this.accountsFile, JSON.stringify(this.accounts, null, 2));
    }
    
    saveProxies() {
        fs.writeFileSync(this.proxiesFile, JSON.stringify(this.proxies, null, 2));
    }
    
    saveSettings() {
        fs.writeFileSync(this.settingsFile, JSON.stringify(this.settings, null, 2));
    }
    
    saveReports() {
        fs.writeFileSync(this.reportsFile, JSON.stringify(this.reports, null, 2));
    }
    
    // ============ ACCOUNT MANAGEMENT ============
    
    addAccount(email, password) {
        const newId = this.accounts.length > 0 ? Math.max(...this.accounts.map(a => a.id)) + 1 : 1;
        
        const account = {
            id: newId,
            email: email,
            password: this.encrypt(password),
            status: 'active',
            used_today: 0,
            total_actions: 0,
            success_count: 0,
            fail_count: 0,
            last_used: null,
            created_at: new Date().toISOString(),
            notes: ''
        };
        
        this.accounts.push(account);
        this.saveAccounts();
        logger.info(`✅ Added account: ${email}`);
        
        return { id: account.id, email: account.email, status: account.status };
    }
    
    addAccountsBulk(accountsList) {
        const added = [];
        for (const { email, password } of accountsList) {
            const result = this.addAccount(email, password);
            added.push(result);
        }
        return added;
    }
    
    removeAccount(id) {
        const index = this.accounts.findIndex(a => a.id === parseInt(id));
        if (index !== -1) {
            const removed = this.accounts.splice(index, 1)[0];
            this.saveAccounts();
            logger.info(`🗑️ Removed account: ${removed.email}`);
            return { success: true, email: removed.email };
        }
        return { success: false };
    }
    
    removeAllAccounts() {
        const count = this.accounts.length;
        this.accounts = [];
        this.saveAccounts();
        logger.info(`🗑️ Removed all ${count} accounts`);
        return { success: true, removed: count };
    }
    
    getAccount(id) {
        const account = this.accounts.find(a => a.id === parseInt(id));
        if (account) {
            return {
                ...account,
                password: this.decrypt(account.password)
            };
        }
        return null;
    }
    
    getAllAccounts() {
        return this.accounts.map(a => ({
            id: a.id,
            email: a.email,
            status: a.status,
            used_today: a.used_today,
            total_actions: a.total_actions,
            success_count: a.success_count,
            fail_count: a.fail_count,
            success_rate: a.total_actions > 0 ? ((a.success_count / a.total_actions) * 100).toFixed(1) : 0
        }));
    }
    
    getAvailableAccounts(limit = 500) {
        const now = new Date();
        const currentHour = now.getHours();
        
        const available = this.accounts.filter(account => {
            if (account.status !== 'active') return false;
            if (account.used_today >= config.MAX_ACTIONS_PER_DAY) return false;
            
            if (account.last_used) {
                const lastUsed = new Date(account.last_used);
                const minutesSinceLastUse = (now - lastUsed) / (1000 * 60);
                if (minutesSinceLastUse < config.COOLDOWN_MINUTES) return false;
            }
            
            // Safe hours bonus
            if (currentHour >= config.SAFE_HOURS_START && currentHour <= config.SAFE_HOURS_END) {
                return true;
            }
            
            return account.used_today < 100;
        });
        
        // Sort by least used first (rotation)
        available.sort((a, b) => a.used_today - b.used_today);
        
        const result = available.slice(0, limit).map(acc => ({
            ...acc,
            password: this.decrypt(acc.password)
        }));
        
        logger.info(`📊 Available accounts: ${result.length}/${this.accounts.length}`);
        return result;
    }
    
    updateAccountUsage(accountId, success) {
        const account = this.accounts.find(a => a.id === accountId);
        if (account) {
            account.last_used = new Date().toISOString();
            if (success) {
                account.used_today++;
                account.success_count++;
            } else {
                account.fail_count++;
                if (account.fail_count >= 5) {
                    account.status = 'suspicious';
                }
            }
            account.total_actions++;
            this.saveAccounts();
            
            this.settings.total_actions++;
            if (success) this.settings.total_reports++;
            this.saveSettings();
        }
    }
    
    updateAccountStatus(id, status) {
        const account = this.accounts.find(a => a.id === parseInt(id));
        if (account) {
            account.status = status;
            this.saveAccounts();
            logger.info(`📝 Account ${account.email} status changed to ${status}`);
            return true;
        }
        return false;
    }
    
    resetDailyCounters() {
        for (const account of this.accounts) {
            account.used_today = 0;
            if (account.status === 'suspicious' && account.fail_count < 10) {
                account.status = 'active';
            }
        }
        this.settings.last_reset = new Date().toISOString();
        this.saveAccounts();
        this.saveSettings();
        logger.info('🔄 Daily counters reset');
    }
    
    checkAndResetDaily() {
        const lastReset = new Date(this.settings.last_reset);
        const now = new Date();
        if (lastReset.getDate() !== now.getDate()) {
            this.resetDailyCounters();
        }
    }
    
    // ============ PROXY MANAGEMENT ============
    
    addProxy(server, port, username = null, password = null) {
        const newId = this.proxies.length > 0 ? Math.max(...this.proxies.map(p => p.id)) + 1 : 1;
        
        const proxy = {
            id: newId,
            server,
            port,
            username,
            password: password ? this.encrypt(password) : null,
            is_active: true,
            usage_count: 0,
            last_used: null,
            created_at: new Date().toISOString()
        };
        
        this.proxies.push(proxy);
        this.saveProxies();
        logger.info(`✅ Added proxy: ${server}:${port}`);
        
        return proxy;
    }
    
    getRandomProxy() {
        const activeProxies = this.proxies.filter(p => p.is_active);
        if (activeProxies.length === 0) return null;
        
        const proxy = activeProxies[Math.floor(Math.random() * activeProxies.length)];
        return {
            server: proxy.server,
            port: proxy.port,
            username: proxy.username,
            password: proxy.password ? this.decrypt(proxy.password) : null
        };
    }
    
    removeProxy(id) {
        const index = this.proxies.findIndex(p => p.id === parseInt(id));
        if (index !== -1) {
            const removed = this.proxies.splice(index, 1)[0];
            this.saveProxies();
            logger.info(`🗑️ Removed proxy: ${removed.server}:${removed.port}`);
            return { success: true };
        }
        return { success: false };
    }
    
    // ============ REPORT HISTORY ============
    
    addReportRecord(videoUrl, successCount, totalCount, reason) {
        const record = {
            id: this.reports.length + 1,
            video_url: videoUrl,
            success_count: successCount,
            total_count: totalCount,
            reason: reason,
            timestamp: new Date().toISOString()
        };
        this.reports.push(record);
        this.saveReports();
        return record;
    }
    
    getRecentReports(limit = 20) {
        return this.reports.slice(-limit).reverse();
    }
    
    // ============ STATISTICS ============
    
    getStats() {
        const total = this.accounts.length;
        const active = this.accounts.filter(a => a.status === 'active').length;
        const suspicious = this.accounts.filter(a => a.status === 'suspicious').length;
        const banned = this.accounts.filter(a => a.status === 'banned').length;
        const actionsToday = this.accounts.reduce((sum, a) => sum + (a.used_today || 0), 0);
        const totalActions = this.accounts.reduce((sum, a) => sum + (a.total_actions || 0), 0);
        const successRate = totalActions > 0 ? 
            (this.accounts.reduce((sum, a) => sum + (a.success_count || 0), 0) / totalActions * 100).toFixed(2) : 0;
        
        const uptime = Math.floor((new Date() - new Date(this.settings.start_time)) / 1000 / 60 / 60);
        
        return {
            total,
            active,
            suspicious,
            banned,
            actions_today: actionsToday,
            total_actions: totalActions,
            total_reports: this.settings.total_reports,
            success_rate: successRate,
            proxies_available: this.proxies.length,
            bot_status: this.settings.bot_status || 'online',
            uptime_hours: uptime,
            last_reset: this.settings.last_reset
        };
    }
}

module.exports = AccountManager;
