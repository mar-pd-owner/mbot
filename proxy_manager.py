const axios = require('axios');
const fs = require('fs');
const config = require('./config');

class FreeProxyManager {
    constructor() {
        this.proxies = [];
        this.lastUpdate = null;
        this.loadFromCache();
    }
    
    loadFromCache() {
        try {
            if (fs.existsSync('./data/proxies.json')) {
                const data = JSON.parse(fs.readFileSync('./data/proxies.json'));
                this.proxies = data.proxies || [];
                this.lastUpdate = data.lastUpdate;
                console.log(`📦 ক্যাশে থেকে ${this.proxies.length} টি প্রক্সি লোড হয়েছে`);
            }
        } catch(e) {}
    }
    
    saveToCache() {
        fs.writeFileSync('./data/proxies.json', JSON.stringify({
            proxies: this.proxies,
            lastUpdate: this.lastUpdate
        }, null, 2));
    }
    
    async fetchFreeProxies() {
        console.log('🔄 ফ্রি প্রক্সি সংগ্রহ করা হচ্ছে...');
        const allProxies = new Set();
        
        for (const apiUrl of config.FREE_PROXY_APIS) {
            try {
                const response = await axios.get(apiUrl, { timeout: 10000 });
                const lines = response.data.split('\n');
                
                for (const line of lines) {
                    const proxy = line.trim();
                    if (proxy && proxy.includes(':')) {
                        // ফরম্যাট চেক: ip:port
                        const [ip, port] = proxy.split(':');
                        if (ip && port && !isNaN(port) && port > 0 && port < 65535) {
                            allProxies.add(proxy);
                        }
                    }
                }
                console.log(`  ✓ ${apiUrl.split('/')[2]} থেকে প্রক্সি নেওয়া হয়েছে`);
            } catch(e) {
                console.log(`  ✗ ${apiUrl.split('/')[2]} ব্যর্থ`);
            }
        }
        
        this.proxies = Array.from(allProxies).slice(0, config.MAX_PROXIES);
        this.lastUpdate = new Date().toISOString();
        this.saveToCache();
        
        console.log(`✅ মোট ${this.proxies.length} টি ফ্রি প্রক্সি সংগ্রহ করা হয়েছে`);
        return this.proxies;
    }
    
    getRandomProxy() {
        if (this.proxies.length === 0) return null;
        return this.proxies[Math.floor(Math.random() * this.proxies.length)];
    }
    
    getProxyList(limit = 100) {
        return this.proxies.slice(0, limit);
    }
    
    async refreshIfNeeded() {
        if (!this.lastUpdate) {
            await this.fetchFreeProxies();
            return;
        }
        
        const last = new Date(this.lastUpdate);
        const now = new Date();
        const minutesDiff = (now - last) / 1000 / 60;
        
        if (minutesDiff > config.PROXY_REFRESH_INTERVAL) {
            await this.fetchFreeProxies();
        }
    }
}

module.exports = FreeProxyManager;
