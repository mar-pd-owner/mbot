// bot.js
const { Telegraf, Markup } = require('telegraf');
const axios = require('axios');
const config = require('./config');
const logger = require('./logger');
const AccountManager = require('./account-manager');
const URLExtractor = require('./url-extractor');

const bot = new Telegraf(config.TELEGRAM_BOT_TOKEN);
const accountManager = new AccountManager();

const API_URL = `http://${config.API_HOST}:${config.PORT}`;

// ============ MIDDLEWARE ============
bot.use(async (ctx, next) => {
    logger.info(`User: ${ctx.from.id} | Command: ${ctx.message?.text || 'unknown'}`);
    await next();
});

// ============ START COMMAND ============
bot.start(async (ctx) => {
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('📊 Stats', 'stats')],
        [Markup.button.callback('📝 Report', 'report_menu')],
        [Markup.button.callback('➕ Add Account', 'add_account')],
        [Markup.button.callback('📋 Accounts List', 'list_accounts')],
        [Markup.button.callback('⚠️ Disclaimer', 'disclaimer')]
    ]);
    
    await ctx.replyWithHTML(`
🤖 *${config.BOT_NAME} - Professional TikTok Automation Bot* 🤖
        
*Author:* ${config.BOT_AUTHOR}
*Version:* ${config.BOT_VERSION}

*Available Commands:*
/report <url> - Report a video
/mass <url> [count] - Mass report
/add <email> <password> - Add new account
/stats - Show bot stats
/accounts - List all accounts
/disclaimer - Show disclaimer

⚡ *Bot is ready to use!*
    `, keyboard);
});

// ============ DISCLAIMER ============
bot.command('disclaimer', async (ctx) => {
    await ctx.replyWithHTML(config.DISCLAIMER);
});

bot.action('disclaimer', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.replyWithHTML(config.DISCLAIMER);
});

// ============ STATS ============
bot.command('stats', async (ctx) => {
    try {
        const response = await axios.get(`${API_URL}/api/stats`);
        const stats = response.data;
        
        await ctx.replyWithHTML(`
📊 *${config.BOT_NAME} Statistics* 📊

┌ *Accounts*
├ 📧 Total: ${stats.total}
├ ✅ Active: ${stats.active}
├ ⚠️ Suspicious: ${stats.suspicious}
├ ❌ Banned: ${stats.banned}
└ 📈 Actions Today: ${stats.actions_today}

┌ *Performance*
├ 🔄 Total Actions: ${stats.total_actions}
├ 📊 Success Rate: ${stats.success_rate}%
└ 🌐 Proxies: ${stats.proxies_available}

*Status:* ${stats.bot_status === 'online' ? '🟢 ONLINE' : '🔴 OFFLINE'}
        `);
    } catch (error) {
        await ctx.reply('❌ Failed to fetch stats. API may be offline.');
    }
});

bot.action('stats', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/stats');
});

// ============ ADD ACCOUNT ============
bot.command('add', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 3) {
        await ctx.reply('❌ Usage: /add <email> <password>\nExample: /add user@gmail.com pass123');
        return;
    }
    
    const email = args[1];
    const password = args.slice(2).join(' ');
    
    try {
        const response = await axios.post(`${API_URL}/api/account/add`, { email, password });
        
        if (response.data.success) {
            await ctx.replyWithHTML(`
✅ *Account Added Successfully!*

📧 Email: ${email}
🆔 ID: ${response.data.account.id}
📅 Created: ${response.data.account.created_at}

*Total Accounts:* ${accountManager.getStats().total}
            `);
            logger.info(`New account added by ${ctx.from.id}: ${email}`);
        } else {
            await ctx.reply('❌ Failed to add account.');
        }
    } catch (error) {
        await ctx.reply(`❌ Error: ${error.response?.data?.error || error.message}`);
    }
});

bot.action('add_account', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('Please use: /add email password\n\nExample: /add user@gmail.com pass123');
});

// ============ REPORT ============
bot.command('report', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 2) {
        await ctx.reply('❌ Usage: /report <url>\n\nSupports both full and short URLs (vt.tiktok.com)');
        return;
    }
    
    const url = args[1];
    const statusMsg = await ctx.reply('⏳ Processing your report...');
    
    try {
        const response = await axios.post(`${API_URL}/api/report`, { url });
        
        if (response.data.success) {
            await ctx.telegram.editMessageText(
                ctx.chat.id,
                statusMsg.message_id,
                null,
                `
✅ *Report Submitted Successfully!*

🎥 Video: ${response.data.video_url}
👤 Account: ${response.data.account}
⚠️ Reason: ${response.data.reason}

*Status:* Report has been sent to TikTok moderation.
                `,
                { parse_mode: 'Markdown' }
            );
        } else {
            await ctx.telegram.editMessageText(
                ctx.chat.id,
                statusMsg.message_id,
                null,
                `❌ Report Failed!\n\nError: ${response.data.error || 'Unknown error'}`
            );
        }
    } catch (error) {
        await ctx.telegram.editMessageText(
            ctx.chat.id,
            statusMsg.message_id,
            null,
            `❌ Error: ${error.response?.data?.error || error.message}`
        );
    }
});

// ============ MASS REPORT ============
bot.command('mass', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 2) {
        await ctx.reply('❌ Usage: /mass <url> [count]\n\nExample: /mass https://vt.tiktok.com/xxx 50');
        return;
    }
    
    const url = args[1];
    const count = args[2] ? parseInt(args[2]) : 50;
    
    if (count > 200) {
        await ctx.reply('❌ Maximum 200 reports per mass report.');
        return;
    }
    
    const statusMsg = await ctx.reply(`⚠️ Starting mass report with ${count} accounts...\n\nThis may take several minutes.`);
    
    try {
        const response = await axios.post(`${API_URL}/api/mass-report`, { url, count });
        
        await ctx.telegram.editMessageText(
            ctx.chat.id,
            statusMsg.message_id,
            null,
            `
💀 *Mass Report Completed* 💀

🎥 Video: ${response.data.video_url}
📊 Requested: ${response.data.total_requested}
✅ Successful: ${response.data.successful}
❌ Failed: ${response.data.total_executed - response.data.successful}

*Success Rate:* ${((response.data.successful / response.data.total_executed) * 100).toFixed(1)}%

${response.data.successful > 0 ? '⚠️ Video has been flagged multiple times!' : '⚠️ No reports were submitted.'}
            `,
            { parse_mode: 'Markdown' }
        );
    } catch (error) {
        await ctx.telegram.editMessageText(
            ctx.chat.id,
            statusMsg.message_id,
            null,
            `❌ Mass report failed: ${error.response?.data?.error || error.message}`
        );
    }
});

// ============ ACCOUNTS LIST ============
bot.command('accounts', async (ctx) => {
    try {
        const response = await axios.get(`${API_URL}/api/accounts`);
        const { accounts, total } = response.data;
        
        if (accounts.length === 0) {
            await ctx.reply('📭 No accounts found. Use /add to add accounts.');
            return;
        }
        
        let message = `📋 *Account List* (${total} total)\n\n`;
        
        for (const acc of accounts.slice(0, 20)) {
            const statusEmoji = acc.status === 'active' ? '✅' : acc.status === 'suspicious' ? '⚠️' : '❌';
            message += `${statusEmoji} *${acc.email}*\n`;
            message += `   └ Actions: ${acc.used_today}/day | Success: ${acc.success_rate}%\n`;
        }
        
        if (accounts.length > 20) {
            message += `\n*...and ${accounts.length - 20} more accounts*`;
        }
        
        await ctx.replyWithHTML(message);
    } catch (error) {
        await ctx.reply(`❌ Error: ${error.message}`);
    }
});

bot.action('list_accounts', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/accounts');
});

// ============ REPORT MENU ============
bot.action('report_menu', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply(
        '📝 *Report a Video*\n\nPlease send the video URL in one of these formats:\n\n' +
        '• Full URL: `https://www.tiktok.com/@user/video/123456789`\n' +
        '• Short URL: `https://vt.tiktok.com/ZSxxxxx/`\n\n' +
        'Use: `/report <url>`\n' +
        'Use: `/mass <url> [count]` for mass report',
        { parse_mode: 'Markdown' }
    );
});

// ============ EXTRACT URL (Helper) ============
bot.command('extract', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 2) {
        await ctx.reply('❌ Usage: /extract <short_url>');
        return;
    }
    
    const result = await URLExtractor.extractTikTokUrl(args[1]);
    
    if (result.success) {
        await ctx.replyWithHTML(`
🔗 *URL Extracted*

*Short URL:* ${result.shortUrl}
*Full URL:* ${result.fullUrl}
*Video ID:* ${result.videoId || 'N/A'}
        `);
    } else {
        await ctx.reply(`❌ Failed to extract: ${result.error}`);
    }
});

// ============ HELP ============
bot.help(async (ctx) => {
    await ctx.replyWithHTML(`
🤖 *${config.BOT_NAME} Help Menu* 🤖

*Commands:*
/start - Show welcome message
/help - Show this help menu
/stats - Show bot statistics
/add <email> <pass> - Add new account
/accounts - List all accounts
/report <url> - Report a video
/mass <url> [count] - Mass report (max 200)
/extract <url> - Extract full URL from short URL
/disclaimer - Show disclaimer

*Supported URL Formats:*
• Full: https://www.tiktok.com/@user/video/123456789
• Short: https://vt.tiktok.com/ZSxxxxx/
• Short: https://vm.tiktok.com/ZSxxxxx/

*Need Help?* Contact @${config.BOT_AUTHOR}
    `);
});

// ============ ADMIN COMMANDS ============
if (config.ADMIN_IDS) {
    bot.command('reset', async (ctx) => {
        if (!config.ADMIN_IDS.includes(ctx.from.id)) {
            await ctx.reply('⛔ Admin only command.');
            return;
        }
        
        try {
            await axios.post(`${API_URL}/api/admin/reset`);
            await ctx.reply('✅ Daily counters reset successfully!');
            logger.info(`Daily counters reset by admin: ${ctx.from.id}`);
        } catch (error) {
            await ctx.reply(`❌ Reset failed: ${error.message}`);
        }
    });
    
    bot.command('broadcast', async (ctx) => {
        if (!config.ADMIN_IDS.includes(ctx.from.id)) {
            await ctx.reply('⛔ Admin only command.');
            return;
        }
        
        const message = ctx.message.text.split(' ').slice(1).join(' ');
        if (!message) {
            await ctx.reply('❌ Usage: /broadcast <message>');
            return;
        }
        
        // Broadcast logic here
        await ctx.reply(`📢 Broadcast sent: ${message}`);
    });
}

// ============ ERROR HANDLER ============
bot.catch((err, ctx) => {
    logger.error(`Bot error: ${err.message}`);
    ctx.reply('⚠️ An error occurred. Please try again later.');
});

// Start bot
bot.launch().then(() => {
    logger.info(`🤖 ${config.BOT_NAME} Telegram Bot started!`);
    logger.info(`👤 Admin IDs: ${config.ADMIN_IDS.join(', ')}`);
});

// Enable graceful stop
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

module.exports = bot;
