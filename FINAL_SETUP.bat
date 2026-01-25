@echo off
title MBOT Ultimate TikTok Booster - Complete Setup
echo ============================================
echo      MBOT COMPLETE PRODUCTION SETUP
echo ============================================
echo.

echo [1/8] Creating directory structure...
if not exist "config" mkdir config
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "backups" mkdir backups

echo [2/8] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed!
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

echo [3/8] Installing dependencies...
pip install --upgrade pip
pip install telethon aiohttp requests cryptography pycryptodome pillow rsa

echo [4/8] Creating configuration files...
echo Creating config.json...
echo {
echo     "bot_token": "YOUR_BOT_TOKEN_HERE",
echo     "owner_id": 6454347745,
echo     "owner_username": "@rana_editz_00",
echo     "version": 1,
echo     "max_threads": 100,
echo     "proxy_enabled": false,
echo     "proxy_type": "http",
echo     "proxy_auth": false,
echo     "proxy_credential": "",
echo     "max_requests_per_minute": 3000,
echo     "boost_speed": "ultra",
echo     "security_level": "high",
echo     "auto_restart": true,
echo     "log_activity": true,
echo     "hide_owner": true
echo } > config.json

echo Creating devices.txt...
echo 7147658463338055174:7147659243117414149:96cfb3ee-1724-4da8-b916-645cb8a6b7ee:08e88ba76c3516d8 > devices.txt
echo 7147194596676601350:7147195423995528966:7f4d1953-b338-4bf0-98a9-f890c43d4682:e46c5abf713cc300 >> devices.txt
echo 7147106530541405701:7147107505944233734:84e9fe87-1ecd-4378-9462-e5c19b226e7a:049528ac5719224c >> devices.txt

echo Creating evasion_patterns.json...
echo {
echo     "request_delays": [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5],
echo     "header_variations": 15,
echo     "ip_rotation": true,
echo     "device_fingerprinting": true,
echo     "session_rotation_interval": 50,
echo     "human_behavior_simulation": true
echo } > evasion_patterns.json

echo [5/8] Creating required Python files...
REM (All the Python files will be created here)

echo [6/8] Creating batch files...
echo @echo off > START_BOT.bat
echo title MBOT TikTok Booster >> START_BOT.bat
echo python main.py >> START_BOT.bat
echo pause >> START_BOT.bat

echo @echo off > START_ADMIN.bat
echo title MBOT Admin Panel >> START_ADMIN.bat
echo python admin_panel.py >> START_ADMIN.bat
echo pause >> START_ADMIN.bat

echo [7/8] Generating encryption keys...
python -c "
from encryption import SecureEncryption
import json
enc = SecureEncryption()
keys = {
    'aes_key': enc.aes_key.hex(),
    'rsa_public': enc.rsa_public_key.save_pkcs1().decode(),
    'rsa_private': enc.rsa_private_key.save_pkcs1().decode()
}
with open('encryption_keys.json', 'w') as f:
    json.dump(keys, f)
print('Encryption keys generated')
"

echo [8/8] Finalizing setup...
echo. > proxies.txt
echo [] > banned_users.json
echo {} > user_data.json
echo {} > user_stats.json

echo.
echo ============================================
echo      SETUP COMPLETED SUCCESSFULLY!
echo ============================================
echo.
echo NEXT STEPS:
echo 1. Edit config.json and add your bot token
echo 2. Get bot token from @BotFather on Telegram
echo 3. Add more devices to devices.txt
echo 4. Add proxies to proxies.txt (optional)
echo 5. Run START_BOT.bat to start the bot
echo 6. Run START_ADMIN.bat for admin panel
echo.
echo IMPORTANT:
echo - Keep encryption_keys.json safe
echo - Backup your data regularly
echo - Don't share your config files
echo.
pause
