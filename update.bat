@echo off
:: Move to the folder where the script is located
cd /d %~dp0

echo [1/4] Pulling latest code from GitHub...
git pull origin main

echo [2/4] Installing any new dependencies...
call npm install

echo [3/4] Rebuilding the frontend...
call npm run build

echo [4/4] Restarting the server...
pm2 restart all

echo ========================================
echo SUCCESS: Website is now up to date!
echo ========================================
pause
