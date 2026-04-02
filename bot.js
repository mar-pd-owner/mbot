// bot.js
const { Telegraf, Markup } = require('telegraf');
const axios = require('axios');
const fs = require('fs');
const config = require('./config');

const bot = new Telegraf(config.TELEGRAM_BOT_TOKEN);
const API_URL = `http://localhost:${config.PORT}`;

// স্টার্ট কমান্ড
bot.start(async (ctx) => {
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('📊 Status', 'stats')],
        [Markup.button.callback('💀 Mass Report', 'mass_report')],
        [Markup.button.callback('📧 Accounts', 'accounts_menu')],
        [Markup.button.callback('🔄 Refresh Proxies', 'refresh_proxies')],
        [Markup.button.callback('⚠️ Disclaimer', 'disclaimer')]
    ]);
    
    await ctx.replyWithHTML(`
🤖 *${config.BOT_NAME} - Mass Report Bot* 🤖

*Status:* 🟢 ONLINE
*Author:* ${config.BOT_AUTHOR}

*Commands:*
/report <url> - Single report
/mass <url> [count] - Mass report
/add <email> <pass> - Add account
/accounts - List accounts
/stats - Bot stats
    `, keyboard);
});

// ডিসক্লেইমার
bot.command('disclaimer', async (ctx) => {
    await ctx.replyWithHTML(config.DISCLAIMER);
});

bot.action('disclaimer', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.replyWithHTML(config.DISCLAIMER);
});

// স্ট্যাটাস
bot.command('stats', async (ctx) => {
    try {
        const res = await axios.get(`${API_URL}/api/stats`);
        const stats = res.data;
        
        let accounts = [];
        try {
            accounts = JSON.parse(fs.readFileSync('./data/accounts.json', 'utf8'));
        } catch(e) {}
        
        const active = accounts.filter(a => a.status !== 'banned').length;
        
        await ctx.replyWithHTML(`
📊 *BOT STATISTICS*

┌ *Accounts*
├ 📧 Total: ${stats.total_accounts}
├ ✅ Active: ${active}
└ 📈 Today: ${accounts.reduce((s,a) => s + (a.used_today || 0), 0)}

┌ *Proxies*
├ 🌐 Available: ${stats.active_proxies}
└ 🔄 Last Update: ${stats.last_proxy_update ? new Date(stats.last_proxy_update).toLocaleTimeString() : 'Never'}

┌ *System*
├ 🟢 Status: ONLINE
└ 🤖 Bot: ${stats.bot}
        `);
    } catch(e) {
        await ctx.reply('❌ Failed to get stats');
    }
});

bot.action('stats', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/stats');
});

// অ্যাকাউন্ট যোগ
bot.command('add', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 3) {
        await ctx.reply('❌ Usage: /add email password');
        return;
    }
    
    const email = args[1];
    const password = args.slice(2).join(' ');
    
    let accounts = [];
    try {
        accounts = JSON.parse(fs.readFileSync('./data/accounts.json', 'utf8'));
    } catch(e) {}
    
    const newId = accounts.length > 0 ? Math.max(...accounts.map(a => a.id)) + 1 : 1;
    
    accounts.push({
        id: newId,
        email: email,
        password: password,
        status: 'active',
        used_today: 0,
        total_reports: 0,
        created_at: new Date().toISOString()
    });
    
    fs.writeFileSync('./data/accounts.json', JSON.stringify(accounts, null, 2));
    
    await ctx.replyWithHTML(`
✅ *ACCOUNT ADDED*

📧 Email: ${email}
🆔 ID: ${newId}
📊 Total: ${accounts.length} accounts
    `);
});

// অ্যাকাউন্ট লিস্ট
bot.command('accounts', async (ctx) => {
    let accounts = [];
    try {
        accounts = JSON.parse(fs.readFileSync('./data/accounts.json', 'utf8'));
    } catch(e) {}
    
    if (accounts.length === 0) {
        await ctx.reply('📭 No accounts. Use /add to add.');
        return;
    }
    
    let msg = `📋 *ACCOUNTS* (${accounts.length})\n\n`;
    
    for (const acc of accounts.slice(0, 20)) {
        const emoji = acc.status === 'active' ? '✅' : acc.status === 'banned' ? '❌' : '⚠️';
        msg += `${emoji} *${acc.email}*\n`;
        msg += `   └ Used: ${acc.used_today || 0}/day | Reports: ${acc.total_reports || 0}\n`;
    }
    
    if (accounts.length > 20) {
        msg += `\n*...and ${accounts.length - 20} more*`;
    }
    
    await ctx.replyWithHTML(msg);
});

bot.action('accounts_menu', async (ctx) => {
    await ctx.answerCbQuery();
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('📋 List All', 'list_accounts')],
        [Markup.button.callback('➕ Add Account', 'add_account_prompt')],
        [Markup.button.callback('🗑️ Remove All', 'remove_all_confirm')],
        [Markup.button.callback('◀️ Back', 'back_main')]
    ]);
    await ctx.reply('📧 *Account Management*', { parse_mode: 'Markdown', ...keyboard });
});

bot.action('list_accounts', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/accounts');
});

bot.action('add_account_prompt', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('Please use: /add email password');
});

bot.action('remove_all_confirm', async (ctx) => {
    await ctx.answerCbQuery();
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('✅ YES', 'remove_all_execute')],
        [Markup.button.callback('❌ NO', 'accounts_menu')]
    ]);
    await ctx.reply('⚠️ *Remove ALL accounts?*', { parse_mode: 'Markdown', ...keyboard });
});

bot.action('remove_all_execute', async (ctx) => {
    await ctx.answerCbQuery();
    fs.writeFileSync('./data/accounts.json', JSON.stringify([], null, 2));
    await ctx.reply('🗑️ All accounts removed!');
});

// সিঙ্গেল রিপোর্ট
bot.command('report', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 2) {
        await ctx.reply('❌ Usage: /report <url>');
        return;
    }
    
    const url = args[1];
    const msg = await ctx.reply('⏳ Processing report...');
    
    try {
        const res = await axios.post(`${API_URL}/api/report`, { url });
        
        if (res.data.success) {
            await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, `
✅ *REPORT SUCCESSFUL!*

🎥 Target: ${url.substring(0, 50)}...
👤 Account: ${res.data.account}

⚠️ TikTok will review this content.
            `, { parse_mode: 'Markdown' });
        } else {
            await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, `❌ Failed: ${res.data.error}`);
        }
    } catch(e) {
        await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, `❌ Error: ${e.message}`);
    }
});

// ম্যাস রিপোর্ট
bot.command('mass', async (ctx) => {
    const args = ctx.message.text.split(' ');
    
    if (args.length < 2) {
        await ctx.reply('❌ Usage: /mass <url> [count]\nExample: /mass https://vt.tiktok.com/xxx 50');
        return;
    }
    
    const url = args[1];
    const count = args[2] ? Math.min(parseInt(args[2]), 500) : 100;
    
    const msg = await ctx.reply(`💀 Starting mass report with ${count} accounts...\nThis may take several minutes.`);
    
    try {
        const res = await axios.post(`${API_URL}/api/mass-report`, { url, count });
        
        await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, `
💀 *MASS REPORT COMPLETED* 💀

🎥 Target: ${url.substring(0, 50)}...
📊 Total: ${res.data.total}
✅ Success: ${res.data.successful}
❌ Failed: ${res.data.failed}
📈 Success Rate: ${res.data.success_rate}%

${res.data.successful > 0 ? '⚠️ Video has been flagged!' : '⚠️ No reports submitted.'}
            `, { parse_mode: 'Markdown' });
    } catch(e) {
        await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, `❌ Failed: ${e.response?.data?.error || e.message}`);
    }
});

bot.action('mass_report', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('💀 Use: /mass <url> [count]\nExample: /mass https://vt.tiktok.com/xxx 100');
});

// প্রক্সি রিফ্রেশ
bot.command('refresh_proxies', async (ctx) => {
    const msg = await ctx.reply('🔄 Fetching fresh proxies...');
    
    try {
        await axios.post(`${API_URL}/api/proxy/refresh`);
        await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, '✅ Proxies refreshed successfully!');
    } catch(e) {
        await ctx.telegram.editMessageText(ctx.chat.id, msg.message_id, null, '❌ Failed to refresh proxies');
    }
});

bot.action('refresh_proxies', async (ctx) => {
    await ctx.answerCbQuery();
    await ctx.reply('/refresh_proxies');
});

// ব্যাক টু মেইন
bot.action('back_main', async (ctx) => {
    await ctx.answerCbQuery();
    const keyboard = Markup.inlineKeyboard([
        [Markup.button.callback('📊 Status', 'stats'), Markup.button.callback('💀 Mass Report', 'mass_report')],
        [Markup.button.callback('📧 Accounts', 'accounts_menu'), Markup.button.callback('🔄 Refresh Proxies', 'refresh_proxies')],
        [Markup.button.callback('⚠️ Disclaimer', 'disclaimer')]
    ]);
    await ctx.reply(`💀 *${config.BOT_NAME}* - Main Menu`, { parse_mode: 'Markdown', ...keyboard });
});

// অ্যাডমিন কমান্ড
bot.command('reset', async (ctx) => {
    if (!config.ADMIN_IDS.includes(ctx.from.id)) {
        await ctx.reply('⛔ Admin only');
        return;
    }
    
    let accounts = [];
    try {
        accounts = JSON.parse(fs.readFileSync('./data/accounts.json', 'utf8'));
    } catch(e) {}
    
    for (const acc of accounts) {
        acc.used_today = 0;
    }
    
    fs.writeFileSync('./data/accounts.json', JSON.stringify(accounts, null, 2));
    await ctx.reply('✅ Daily counters reset!');
});

// এরর হ্যান্ডলার
bot.catch((err, ctx) => {
    console.error('Bot error:', err);
});

// স্টার্ট বট
bot.launch().then(() => {
    console.log('🤖 Telegram Bot started!');
    
    // ডিরেক্টরি ক্রিয়েট
    if (!fs.existsSync('./data')) fs.mkdirSync('./data');
    if (!fs.existsSync('./data/accounts.json')) fs.writeFileSync('./data/accounts.json', '[]');
});

process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));

module.exports = bot;
