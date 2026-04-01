// url-extractor.js
const axios = require('axios');
const logger = require('./logger');

class URLExtractor {
    
    static async extractTikTokUrl(shortUrl) {
        /**
         * Extract full TikTok URL from short URL (vt.tiktok.com)
         * Supports: https://vt.tiktok.com/ZSH6hLbGW/
         */
        try {
            logger.info(`Extracting URL: ${shortUrl}`);
            
            // Make request to get redirect location
            const response = await axios.get(shortUrl, {
                maxRedirects: 0,
                validateStatus: (status) => status === 301 || status === 302 || status === 200,
                headers: {
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'
                }
            });
            
            let fullUrl = response.headers.location || response.request.res.responseUrl;
            
            if (!fullUrl && response.status === 200) {
                // Sometimes TikTok serves HTML with meta refresh
                const html = response.data;
                const match = html.match(/<meta[^>]*url=(https?:\/\/[^"]+)/i);
                if (match) {
                    fullUrl = match[1];
                }
            }
            
            if (!fullUrl) {
                throw new Error('Could not extract URL');
            }
            
            // Clean URL
            fullUrl = fullUrl.split('?')[0];
            
            // Validate URL
            if (fullUrl.includes('tiktok.com') && (fullUrl.includes('/video/') || fullUrl.includes('/photo/'))) {
                logger.info(`Extracted full URL: ${fullUrl}`);
                return {
                    success: true,
                    shortUrl: shortUrl,
                    fullUrl: fullUrl,
                    videoId: fullUrl.split('/video/')[1]?.split('?')[0] || null
                };
            }
            
            throw new Error('Invalid TikTok URL');
            
        } catch (error) {
            logger.error(`URL extraction failed: ${error.message}`);
            return {
                success: false,
                shortUrl: shortUrl,
                error: error.message
            };
        }
    }
    
    static async batchExtract(urls) {
        const results = [];
        for (const url of urls) {
            const result = await this.extractTikTokUrl(url);
            results.push(result);
            // Delay to avoid rate limiting
            await new Promise(resolve => setTimeout(resolve, 1000));
        }
        return results;
    }
    
    static isValidShortUrl(url) {
        return url.includes('vt.tiktok.com') || url.includes('vm.tiktok.com');
    }
    
    static extractVideoIdFromUrl(url) {
        const patterns = [
            /\/video\/(\d+)/,
            /\/photo\/(\d+)/,
            /\/t\/([A-Za-z0-9_-]+)/
        ];
        
        for (const pattern of patterns) {
            const match = url.match(pattern);
            if (match) return match[1];
        }
        return null;
    }
}

module.exports = URLExtractor;
