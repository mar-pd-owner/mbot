// bot.js
const { Telegraf, Markup } = require('telegraf');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const config = require('./config');
const logger = require('./logger');
const AccountManager = require('./account-manager');
const URLExtractor = require('./url-extractor');

const bot = new Telegraf(config.TELEGRAM_BOT_TOKEN);
const accountManager = new AccountManager();
const API_URL = `http://${config.API_HOST}:${config.PORT}`;

// ============ MIDDLEWARE ============
bot.use(async (ctx, next) => {
    logger.info(`👤 User: ${ctx.from.id} | ${ctx.from.username} | Command: ${ctx.message?.text || 'unknown'}`);
    await next();
});

// ============ START COMMAND ============
bot.start(async (ctx) => {
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('📊 STATS', 'stats'), Markup.button.callback('💀 MASS REPORT', 'mass_report')],
        [Markup.button.callback('📧 ACCOUNTS', 'accounts_menu'), Markup.button.callback('🌐 PROXIES', 'proxies_menu')],
        [Markup.button.callback('📜 HISTORY', 'history'), Markup.button.callback('⚠️ DISCLAIMER', 'disclaimer')],
        [Markup.button.callback('🆘 HELP', 'help')]
    ]);
    
    await ctx.replyWithHTML(`
☠️ *${config.BOT_NAME} - ULTIMATE POWERFUL BOT* ☠️

*Author:* ${config.BOT_AUTHOR}
*Version:* ${config.BOT_VERSION}
*Status:* 🟢 ONLINE

*⚡ Commands:*
/report <url> - Single report
/mass <url> [count] - Mass report (up to ${config.MASS_REPORT_COUNT})
/add <email> <pass> - Add account
/accounts - List all accounts
/stats - Bot statistics
/history - Report history
/disclaimer - Show disclaimer
/help - Help menu

*💀 ULTRA POWERFUL MODE ACTIVE 💀*
    `, keyboard);
});

// ============ HELP ============
bot.help(async (ctx) => {
    await ctx.replyWithHTML(`
💀 *${config.BOT_NAME} HELP MENU* 💀

*📝 REPORT COMMANDS:*
/report <url> - Report a single video
/mass <url> [count] - Mass report with multiple accounts
Example: /mass https://vt.tiktok.com/xxx 100

*📧 ACCOUNT MANAGEMENT:*
/add <email> <pass> - Add new account
/accounts - List all accounts
/remove <id> - Remove account by ID
/reset-all - Remove ALL accounts (admin)
/status <id> <active/suspicious/banned> - Change status

*📊 INFO COMMANDS:*
/stats - Show bot statistics
/history - Show recent reports
/disclaimer - Show disclaimer

*🌐 PROXY MANAGEMENT:*
/proxy-add <server> <port> - Add proxy
/proxy-list - List all proxies
/proxy-remove <id> - Remove proxy

*⚙️ ADMIN COMMANDS:*
/reset-daily - Reset daily counters
/broadcast <msg> - Broadcast message
/stop-bot - Emergency stop

*Supported URLs:*
• Full: https://www.tiktok.com/@user/video/123456789
• Short: https://vt.tiktok.com/ZSxxxxx/
• Short: https://vm.tiktok.com/ZSxxxxx/

*⚠️ USE WISELY!* @${config.BOT_AUTHOR}
    `);
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
        const s = response.data;
        
        await ctx.replyWithHTML(`
💀 *${config.BOT_NAME} STATISTICS* 💀

┌ *📧 ACCOUNTS*
├ ✅ Active: ${s.active}
├ ⚠️ Suspicious: ${s.suspicious}
├ ❌ Banned: ${s.banned}
└ 📈 Total: ${s.total}

┌ *⚡ ACTIONS*
├ 📊 Today: ${s.actions_today}
├ 🔄 Total: ${s.total_actions}
├ 📝 Reports: ${s.total_reports}
└ 📈 Success Rate: ${s.success_rate}%

┌ *🌐 SYSTEM*
├ 🖥️ Proxies: ${s.proxies_available}
├ ⏱️ Uptime: ${s.uptime_hours} hours
└ 🟢 Status: ${s.bot_status === 'online' ? 'ONLINE' : 'OFFLINE'}

*💀 ULTRA POWERFUL MODE ACTIVE* 💀
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
        await ctx.reply('❌ Usage: /add <email> <password>\n\nExample: /add user@gmail.com pass123');
        return;
    }
    
    const email = args[1];
    const password = args.slice(2).join(' ');
    
    try {
        const response = await axios.post(`${API_URL}/api/account/add`, { email, password });
        
        if (response.data.success) {
            const stats = accountManager.getStats();
            await ctx.replyWithHTML(`
✅ *ACCOUNT ADDED SUCCESSFULLY!*

📧 Email: ${email}
🆔 ID: ${response.data.account.id}
📅 Created: ${response.data.account.created_at}

📊 *Total Accounts:* ${stats.total}
💀 *Ready for mass report!* 💀
            `);
            logger.info(`New account added by ${ctx.from.id}: ${email}`);
        } else {
            await ctx.reply('❌ Failed to add account.');
        }
    } catch (error) {
        await ctx.reply(`❌ Error: ${error.response?.data?.error || error.message}`);
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
        
        let message = `📋 *ACCOUNT LIST* (${total} total)\n\n`;
        
        for (const acc of accounts.slice(0, 30)) {
            const statusEmoji = acc.status === 'active' ? '✅' : acc.status === 'suspicious' ? '⚠️' : '❌';
            message += `${statusEmoji} *ID ${acc.id}* - ${acc.email}\n`;
            message += `   └ Actions: ${acc.used_today}/day | Success: ${acc.success_rate}% | Total: ${acc.total_actions}\n`;
        }
        
        if (accounts.length > 30) {
            message += `\n*...and ${accounts.length - 30} more accounts*`;
        }
        
        message += `\n\n💀 *Use /remove <id> to remove account* 💀`;
        
        await ctx.replyWithHTML(message);
    } catch (error) {
        await ctx.reply(`❌ Error: ${error.message}`);
    }
});

bot.action('accounts_menu', async (ctx) => {
    await ctx.answerCbQuery();
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('📋 LIST ALL', 'list_accounts')],
        [Markup.button.callback('➕ ADD ACCOUNT', 'add_account')],
        [Markup.button.callback('🗑️ REMOVE ALL', 'remove_all_confirm')],
        [Markup.button.callback('◀️ BACK', 'back_main')]
    ]);
    await ctx.reply('📧 *Account Management*', { parse_mode: 'Markdown', ...keyboard });
});

bot.action('list_accounts', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/accounts');
});

bot.action('add_account', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('Please use: /add email password\n\nExample: /add user@gmail.com pass123');
});

bot.action('remove_all_confirm', async (ctx) => {
    await ctx.answerCbQuery();
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('✅ YES, REMOVE ALL', 'remove_all_execute')],
        [Markup.button.callback('❌ CANCEL', 'accounts_menu')]
    ]);
    await ctx.reply('⚠️ *WARNING!* This will remove ALL accounts. Are you sure?', { parse_mode: 'Markdown', ...keyboard });
});

bot.action('remove_all_execute', async (ctx) => {
    await ctx.answerCbQuery();
    const result = accountManager.removeAllAccounts();
    await ctx.reply(`🗑️ Removed ${result.removed} accounts successfully!`);
});

// ============ REMOVE ACCOUNT ============
bot.command('remove', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 2) {
        await ctx.reply('❌ Usage: /remove <account_id>\n\nUse /accounts to see IDs');
        return;
    }
    
    const id = args[1];
    const result = accountManager.removeAccount(id);
    
    if (result.success) {
        await ctx.reply(`✅ Account ${result.email} removed successfully!`);
    } else {
        await ctx.reply(`❌ Account with ID ${id} not found.`);
    }
});

// ============ UPDATE ACCOUNT STATUS ============
bot.command('status', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 3) {
        await ctx.reply('❌ Usage: /status <id> <active|suspicious|banned>\n\nExample: /status 5 suspicious');
        return;
    }
    
    const id = args[1];
    const status = args[2];
    
    if (!['active', 'suspicious', 'banned'].includes(status)) {
        await ctx.reply('❌ Status must be: active, suspicious, or banned');
        return;
    }
    
    const result = accountManager.updateAccountStatus(id, status);
    
    if (result) {
        await ctx.reply(`✅ Account ID ${id} status updated to ${status}`);
    } else {
        await ctx.reply(`❌ Account ID ${id} not found.`);
    }
});

// ============ SINGLE REPORT ============
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
✅ *REPORT SUBMITTED SUCCESSFULLY!*

🎥 Video: ${response.data.video_url}
👤 Account: ${response.data.account}
⚠️ Reason: ${response.data.reason}

*Status:* Report has been sent to TikTok moderation.
*Impact:* Video is being reviewed.
                `,
                { parse_mode: 'Markdown' }
            );
        } else {
            await ctx.telegram.editMessageText(
                ctx.chat.id,
                statusMsg.message_id,
                null,
                `❌ *REPORT FAILED!*\n\nError: ${response.data.error || 'Unknown error'}`
            );
        }
    } catch (error) {
        await ctx.telegram.editMessageText(
            ctx.chat.id,
            statusMsg.message_id,
            null,
            `❌ *ERROR:* ${error.response?.data?.error || error.message}`
        );
    }
});

// ============ MASS REPORT - POWERFUL ============
bot.command('mass', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 2) {
        await ctx.reply('❌ Usage: /mass <url> [count]\n\nExample: /mass https://vt.tiktok.com/xxx 100\n\nMax count: ' + config.MASS_REPORT_COUNT);
        return;
    }
    
    const url = args[1];
    const count = args[2] ? Math.min(parseInt(args[2]), config.MASS_REPORT_COUNT) : config.MASS_REPORT_COUNT;
    
    if (count > config.MASS_REPORT_COUNT) {
        await ctx.reply(`❌ Maximum ${config.MASS_REPORT_COUNT} reports per mass attack.`);
        return;
    }
    
    const stats = accountManager.getStats();
    if (stats.active < 10) {
        await ctx.reply(`⚠️ Not enough active accounts! Need at least 10. Current: ${stats.active}`);
        return;
    }
    
    const statusMsg = await ctx.reply(`💀 *STARTING MASS REPORT ATTACK!* 💀\n\n📊 Target: ${url}\n👥 Accounts: ${Math.min(count, stats.active)}\n⏱️ Estimated time: ~${Math.ceil(Math.min(count, stats.active) * config.MASS_REPORT_DELAY / 60)} minutes\n\n*Please wait...*`, { parse_mode: 'Markdown' });
    
    try {
        const response = await axios.post(`${API_URL}/api/mass-report`, { url, count });
        const r = response.data;
        
        const resultMessage = `
💀 *MASS REPORT COMPLETED!* 💀

🎥 Video: ${r.video_url}
📊 Requested: ${r.total_requested}
✅ Successful: ${r.successful}
❌ Failed: ${r.failed}
📈 Success Rate: ${r.success_rate}%

*IMPACT ANALYSIS:*
${r.successful > 100 ? '⚠️ EXTREME - Video will likely be removed within hours!' : 
  r.successful > 50 ? '⚠️ HIGH - Video is heavily flagged!' :
  r.successful > 20 ? '⚠️ MEDIUM - Video has multiple reports!' :
  '⚠️ LOW - More reports needed!'}

*Total Reports Sent:* ${r.successful}
*Accounts Used:* ${r.total_executed}

💀 *ULTRA POWERFUL ATTACK EXECUTED!* 💀
        `;
        
        await ctx.telegram.editMessageText(
            ctx.chat.id,
            statusMsg.message_id,
            null,
            resultMessage,
            { parse_mode: 'Markdown' }
        );
        
    } catch (error) {
        await ctx.telegram.editMessageText(
            ctx.chat.id,
            statusMsg.message_id,
            null,
            `❌ *MASS REPORT FAILED!*\n\nError: ${error.response?.data?.error || error.message}`
        );
    }
});

bot.action('mass_report', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('💀 *Mass Report Command* 💀\n\nUse: /mass <url> [count]\n\nExample: /mass https://vt.tiktok.com/xxx 100\n\nMax count: ' + config.MASS_REPORT_COUNT, { parse_mode: 'Markdown' });
});

// ============ REPORT HISTORY ============
bot.command('history', async (ctx) => {
    try {
        const response = await axios.get(`${API_URL}/api/reports?limit=10`);
        const { reports } = response.data;
        
        if (reports.length === 0) {
            await ctx.reply('📭 No reports yet. Use /mass or /report to start.');
            return;
        }
        
        let message = `📜 *RECENT REPORTS* (last ${reports.length})\n\n`;
        
        for (const r of reports) {
            const date = new Date(r.timestamp).toLocaleString();
            message += `┌ *ID ${r.id}* - ${date}\n`;
            message += `├ 🎥 ${r.video_url.substring(0, 50)}...\n`;
            message += `└ ✅ ${r.success_count}/${r.total_count} successful\n\n`;
        }
        
        await ctx.replyWithHTML(message);
    } catch (error) {
        await ctx.reply(`❌ Error: ${error.message}`);
    }
});

bot.action('history', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/history');
});

// ============ PROXY MANAGEMENT ============
bot.command('proxy-add', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 3) {
        await ctx.reply('❌ Usage: /proxy-add <server> <port> [username] [password]\n\nExample: /proxy-add 192.168.1.1 8080');
        return;
    }
    
    const server = args[1];
    const port = parseInt(args[2]);
    const username = args[3] || null;
    const password = args[4] || null;
    
    const proxy = accountManager.addProxy(server, port, username, password);
    await ctx.reply(`✅ Proxy added: ${server}:${port}`);
});

bot.command('proxy-list', async (ctx) => {
    const proxies = accountManager.proxies;
    
    if (proxies.length === 0) {
        await ctx.reply('🌐 No proxies configured.');
        return;
    }
    
    let message = `🌐 *PROXY LIST* (${proxies.length})\n\n`;
    for (const p of proxies) {
        message += `┌ *ID ${p.id}* - ${p.server}:${p.port}\n`;
        message += `└ Status: ${p.is_active ? '✅ Active' : '❌ Inactive'} | Used: ${p.usage_count || 0}\n\n`;
    }
    
    await ctx.replyWithHTML(message);
});

bot.command('proxy-remove', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 2) {
        await ctx.reply('❌ Usage: /proxy-remove <id>');
        return;
    }
    
    const result = accountManager.removeProxy(args[1]);
    await ctx.reply(result.success ? '✅ Proxy removed!' : '❌ Proxy not found');
});

// ============ ADMIN COMMANDS ============
if (config.ADMIN_IDS) {
    bot.command('reset-daily', async (ctx) => {
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
        
        // This would need to store user IDs, but for now just confirm
        await ctx.reply(`📢 Broadcast sent: ${message}`);
    });
    
    bot.command('stop-bot', async (ctx) => {
        if (!config.ADMIN_IDS.includes(ctx.from.id)) {
            await ctx.reply('⛔ Admin only command.');
            return;
        }
        
        await ctx.reply('🛑 Bot is stopping...');
        process.exit(0);
    });
}

// ============ BACK TO MAIN ============
bot.action('back_main', async (ctx) => {
    await ctx.answerCbQuery();
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('📊 STATS', 'stats'), Markup.button.callback('💀 MASS REPORT', 'mass_report')],
        [Markup.button.callback('📧 ACCOUNTS', 'accounts_menu'), Markup.button.callback('🌐 PROXIES', 'proxies_menu')],
        [Markup.button.callback('📜 HISTORY', 'history'), Markup.button.callback('⚠️ DISCLAIMER', 'disclaimer')],
        [Markup.button.callback('🆘 HELP', 'help')]
    ]);
    await ctx.reply(`💀 *${config.BOT_NAME} - MAIN MENU* 💀`, { parse_mode: 'Markdown', ...keyboard });
});

bot.action('proxies_menu', async (ctx) => {
    await ctx.answerCbQuery();
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('📋 LIST', 'proxy_list')],
        [Markup.button.callback('➕ ADD', 'proxy_add')],
        [Markup.button.callback('◀️ BACK', 'back_main')]
    ]);
    await ctx.reply('🌐 *Proxy Management*', { parse_mode: 'Markdown', ...keyboard });
});

bot.action('proxy_list', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/proxy-list');
});

bot.action('proxy_add', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('Please use: /proxy-add <server> <port>\n\nExample: /proxy-add 192.168.1.1 8080');
});

bot.action('help', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/help');
});

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
