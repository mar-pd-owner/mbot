// url-extractor.js
const axios = require('axios');
const logger = require('./logger');

class URLExtractor {
    
    static async extractTikTokUrl(shortUrl) {
        try {
            logger.info(`Extracting URL: ${shortUrl}`);
            
            const response = await axios.get(shortUrl, {
                maxRedirects: 0,
                validateStatus: (status) => status === 301 || status === 302 || status === 200,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
                },
                timeout: 15000
            });
            
            let fullUrl = response.headers.location || response.request.res.responseUrl;
            
            if (!fullUrl && response.status === 200) {
                const html = response.data;
                const match = html.match(/<meta[^>]*url=(https?:\/\/[^"]+)/i);
                if (match) fullUrl = match[1];
            }
            
            if (!fullUrl) {
                throw new Error('Could not extract URL');
            }
            
            fullUrl = fullUrl.split('?')[0];
            
            if (fullUrl.includes('tiktok.com') && (fullUrl.includes('/video/') || fullUrl.includes('/photo/'))) {
                const videoId = fullUrl.split('/video/')[1]?.split('?')[0] || 
                               fullUrl.split('/photo/')[1]?.split('?')[0] || null;
                
                logger.info(`✅ Extracted: ${fullUrl}`);
                return { success: true, shortUrl, fullUrl, videoId };
            }
            
            throw new Error('Invalid TikTok URL');
            
        } catch (error) {
            logger.error(`❌ Extraction failed: ${error.message}`);
            return { success: false, shortUrl, error: error.message };
        }
    }
    
    static isValidShortUrl(url) {
        return url.includes('vt.tiktok.com') || url.includes('vm.tiktok.com');
    }
    
    static async batchExtract(urls) {
        const results = [];
        for (const url of urls) {
            const result = await this.extractTikTokUrl(url);
            results.push(result);
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        return results;
    }
}

module.exports = URLExtractor;
