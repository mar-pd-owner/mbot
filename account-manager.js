// account-manager.js
const fs = require('fs');
const path = require('path');
const CryptoJS = require('crypto-js');
const logger = require('./logger');
const config = require('./config');

class AccountManager {
    constructor() {
        this.accountsFile = path.join(__dirname, 'data', 'accounts.json');
        this.proxiesFile = path.join(__dirname, 'data', 'proxies.json');
        this.settingsFile = path.join(__dirname, 'data', 'settings.json');
        
        this.accounts = [];
        this.proxies = [];
        this.settings = {};
        
        this.loadData();
    }
    
    encrypt(text) {
        return CryptoJS.AES.encrypt(text, config.ENCRYPTION_KEY).toString();
    }
    
    decrypt(encrypted) {
        const bytes = CryptoJS.AES.decrypt(encrypted, config.ENCRYPTION_KEY);
        return bytes.toString(CryptoJS.enc.Utf8);
    }
    
    loadData() {
        try {
            if (fs.existsSync(this.accountsFile)) {
                const data = fs.readFileSync(this.accountsFile, 'utf8');
                this.accounts = JSON.parse(data);
                logger.info(`Loaded ${this.accounts.length} accounts`);
            }
        } catch (error) {
            logger.error(`Error loading accounts: ${error.message}`);
            this.accounts = [];
        }
        
        try {
            if (fs.existsSync(this.proxiesFile)) {
                const data = fs.readFileSync(this.proxiesFile, 'utf8');
                this.proxies = JSON.parse(data);
                logger.info(`Loaded ${this.proxies.length} proxies`);
            }
        } catch (error) {
            this.proxies = [];
        }
        
        try {
            if (fs.existsSync(this.settingsFile)) {
                const data = fs.readFileSync(this.settingsFile, 'utf8');
                this.settings = JSON.parse(data);
            }
        } catch (error) {
            this.settings = {
                total_actions: 0,
                last_reset: new Date().toISOString(),
                bot_status: 'online'
            };
        }
    }
    
    saveAccounts() {
        try {
            fs.writeFileSync(this.accountsFile, JSON.stringify(this.accounts, null, 2));
            logger.info('Accounts saved successfully');
        } catch (error) {
            logger.error(`Error saving accounts: ${error.message}`);
        }
    }
    
    saveProxies() {
        try {
            fs.writeFileSync(this.proxiesFile, JSON.stringify(this.proxies, null, 2));
        } catch (error) {
            logger.error(`Error saving proxies: ${error.message}`);
        }
    }
    
    saveSettings() {
        try {
            fs.writeFileSync(this.settingsFile, JSON.stringify(this.settings, null, 2));
        } catch (error) {
            logger.error(`Error saving settings: ${error.message}`);
        }
    }
    
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
        logger.info(`New account added: ${email}`);
        
        return {
            id: account.id,
            email: account.email,
            status: account.status,
            created_at: account.created_at
        };
    }
    
    getAccount(id) {
        const account = this.accounts.find(a => a.id === id);
        if (account) {
            return {
                ...account,
                password: this.decrypt(account.password)
            };
        }
        return null;
    }
    
    getAvailableAccounts(limit = 10) {
        const now = new Date();
        const currentHour = now.getHours();
        
        const available = this.accounts.filter(account => {
            if (account.status !== 'active') return false;
            
            // Daily limit check
            if (account.used_today >= config.MAX_ACTIONS_PER_DAY) return false;
            
            // Cooldown check
            if (account.last_used) {
                const lastUsed = new Date(account.last_used);
                const minutesSinceLastUse = (now - lastUsed) / (1000 * 60);
                if (minutesSinceLastUse < config.COOLDOWN_MINUTES) return false;
            }
            
            // Safe hours bonus
            if (currentHour >= config.SAFE_HOURS_START && currentHour <= config.SAFE_HOURS_END) {
                return true;
            }
            
            // Daytime limit
            return account.used_today < 30;
        });
        
        // Sort by least used first (rotation)
        available.sort((a, b) => a.used_today - b.used_today);
        
        return available.slice(0, limit).map(acc => ({
            ...acc,
            password: this.decrypt(acc.password)
        }));
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
            
            // Update settings
            this.settings.total_actions = (this.settings.total_actions || 0) + 1;
            this.saveSettings();
        }
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
        logger.info('Daily counters reset');
    }
    
    getStats() {
        const total = this.accounts.length;
        const active = this.accounts.filter(a => a.status === 'active').length;
        const suspicious = this.accounts.filter(a => a.status === 'suspicious').length;
        const banned = this.accounts.filter(a => a.status === 'banned').length;
        const actionsToday = this.accounts.reduce((sum, a) => sum + (a.used_today || 0), 0);
        const totalActions = this.accounts.reduce((sum, a) => sum + (a.total_actions || 0), 0);
        const successRate = totalActions > 0 ? 
            (this.accounts.reduce((sum, a) => sum + (a.success_count || 0), 0) / totalActions * 100).toFixed(2) : 0;
        
        return {
            total,
            active,
            suspicious,
            banned,
            actions_today: actionsToday,
            total_actions: totalActions,
            success_rate: successRate,
            proxies_available: this.proxies.length,
            bot_status: this.settings.bot_status || 'online'
        };
    }
    
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
            last_used: null
        };
        
        this.proxies.push(proxy);
        this.saveProxies();
        logger.info(`New proxy added: ${server}:${port}`);
        
        return proxy;
    }
    
    getProxy(id) {
        const proxy = this.proxies.find(p => p.id === id);
        if (proxy && proxy.is_active) {
            return {
                server: proxy.server,
                port: proxy.port,
                username: proxy.username,
                password: proxy.password ? this.decrypt(proxy.password) : null
            };
        }
        return null;
    }
    
    getRandomProxy() {
        const activeProxies = this.proxies.filter(p => p.is_active);
        if (activeProxies.length === 0) return null;
        
        // Round robin selection
        const proxy = activeProxies[Math.floor(Math.random() * activeProxies.length)];
        return this.getProxy(proxy.id);
    }
}

module.exports = AccountManager;
