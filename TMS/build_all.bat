@echo off
cd /d "%~dp0"
echo ========================================
echo Building TMS Host and Client Executables
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo ========================================
echo Building TMS-Host.exe
echo ========================================
echo.

python -m PyInstaller ^
    --name=TMS-Host ^
    --icon=%~dp0assets\logo.ico ^
    --onefile ^
    --console ^
    --clean ^
    --noconfirm ^
    --workpath=build/host ^
    --distpath=dist ^
    --add-data "common;common" ^
    --add-data "host;host" ^
    --add-data "assets;assets" ^
    --add-data "web_module;web_module" ^
    --collect-all uvicorn ^
    --collect-all fastapi ^
    --hidden-import=mysql.connector ^
    --hidden-import=mysql.connector.pooling ^
    --hidden-import=PyQt5.QtCore ^
    --hidden-import=PyQt5.QtGui ^
    --hidden-import=PyQt5.QtWidgets ^
    --hidden-import=PyQt5.QtPrintSupport ^
    --hidden-import=fastapi ^
    --hidden-import=uvicorn ^
    --hidden-import=uvicorn.lifespan.on ^
    --hidden-import=uvicorn.lifespan.off ^
    --hidden-import=uvicorn.protocols.http.auto ^
    --hidden-import=uvicorn.protocols.http.h11_impl ^
    --hidden-import=uvicorn.protocols.websockets.auto ^
    --hidden-import=uvicorn.protocols.websockets.websockets_impl ^
    --hidden-import=bcrypt ^
    --hidden-import=cryptography ^
    --hidden-import=email ^
    --hidden-import=smtplib ^
    --hidden-import=imaplib ^
    --hidden-import=email.mime.text ^
    --hidden-import=email.mime.multipart ^
    --hidden-import=email.header ^
    --hidden-import=email.utils ^
    --hidden-import=ctypes ^
    --hidden-import=ctypes.wintypes ^
    --hidden-import=subprocess ^
    --hidden-import=platform ^
    --hidden-import=hashlib ^
    --hidden-import=pathlib ^
    --hidden-import=threading ^
    --hidden-import=time ^
    --hidden-import=datetime ^
    --hidden-import=json ^
    --hidden-import=collections ^
    --hidden-import=typing ^
    --hidden-import=pydantic ^
    --hidden-import=pydantic.fields ^
    --hidden-import=pydantic.types ^
    --hidden-import=websockets ^
    --hidden-import=asyncio ^
    --hidden-import=common.ui.data_entry_modules ^
    --hidden-import=common.ui.data_entry_modules_transfer_outward_stock ^
    --hidden-import=common.ui.data_entry_window ^
    --hidden-import=common.ui.define_window ^
    --hidden-import=common.ui.invoice_module ^
    --hidden-import=common.ui.main_window ^
    --hidden-import=common.ui.reports_window ^
    --hidden-import=host.ui.dashboard ^
    --hidden-import=host.ui.login_dialog ^
    --hidden-import=host.ui.license_dialog ^
    --hidden-import=host.ui.admin_setup_dialog ^
    --hidden-import=host.ui.styles ^
    --hidden-import=host.data_entry_endpoints ^
    --hidden-import=host.invoice_endpoints ^
    --hidden-import=host.stock_manager ^
    --hidden-import=host.email_service ^
    --hidden-import=host.license_manager ^
    --hidden-import=host.db_pool ^
    --hidden-import=host.api_server ^
    --hidden-import=host.batch_commands ^
    --hidden-import=host.command_endpoints ^
    --hidden-import=host.event_system ^
    --hidden-import=host.snapshot_endpoints ^
    --hidden-import=host.ledger_manager ^
    --hidden-import=common.config ^
    --hidden-import=common.security ^
    --hidden-import=common.utils ^
    --hidden-import=common.realtime_bus ^
    --hidden-import=common.ui.stock_ledgers_module ^
    --hidden-import=common.ui.cash_ledgers_module ^
    --hidden-import=common.ui.voucher_module ^
    --hidden-import=host.voucher_manager ^
    host/main.py

if errorlevel 1 (
    echo.
    echo ERROR: Host build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Building TMS-Client.exe
echo ========================================
echo.

python -m PyInstaller ^
    --name=TMS-Client ^
    --icon=%~dp0assets\logo.ico ^
    --onefile ^
    --windowed ^
    --clean ^
    --noconfirm ^
    --workpath=build/client ^
    --distpath=dist ^
    --add-data "common;common" ^
    --add-data "client;client" ^
    --add-data "assets;assets" ^
    --hidden-import=PyQt5.QtCore ^
    --hidden-import=PyQt5.QtGui ^
    --hidden-import=PyQt5.QtWidgets ^
    --hidden-import=PyQt5.QtPrintSupport ^
    --hidden-import=requests ^
    --hidden-import=urllib3 ^
    --hidden-import=certifi ^
    --hidden-import=charset_normalizer ^
    --hidden-import=idna ^
    --hidden-import=pathlib ^
    --hidden-import=threading ^
    --hidden-import=time ^
    --hidden-import=json ^
    --hidden-import=typing ^
    --hidden-import=websockets ^
    --hidden-import=websockets.client ^
    --hidden-import=asyncio ^
    --hidden-import=client.websocket_client ^
    --hidden-import=common.ui.data_entry_modules ^
    --hidden-import=common.ui.data_entry_modules_transfer_outward_stock ^
    --hidden-import=common.ui.data_entry_window ^
    --hidden-import=common.ui.define_window ^
    --hidden-import=common.ui.invoice_module ^
    --hidden-import=common.ui.main_window ^
    --hidden-import=common.ui.reports_window ^
    --hidden-import=client.ui.login_dialog ^
    --hidden-import=client.api_client ^
    --hidden-import=client.config_loader ^
    --hidden-import=client.websocket_client ^
    --hidden-import=requests.adapters ^
    --hidden-import=urllib3.util.retry ^
    --hidden-import=common.config ^
    --hidden-import=common.security ^
    --hidden-import=common.utils ^
    --hidden-import=common.realtime_bus ^
    --hidden-import=common.ui.stock_ledgers_module ^
    --hidden-import=common.ui.cash_ledgers_module ^
    --hidden-import=common.ui.voucher_module ^
    client/main.py

if errorlevel 1 (
    echo.
    echo ERROR: Client build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo All builds completed successfully!
echo ========================================
echo.
echo Executables location: dist\
echo   - TMS-Host.exe
echo   - TMS-Client.exe
echo.
echo ========================================
echo IMPORTANT: ZeroTier Configuration
echo ========================================
echo.
echo For Client machines, create client_config.json:
echo   {
echo     "host_zerotier_ip": "10.246.76.37",
echo     "port": 8000,
echo     "timeout": 5
echo   }
echo.
echo Place client_config.json in the same directory as TMS-Client.exe
echo.
echo ========================================
echo Icon Cache Note
echo ========================================
echo.
echo If the icon doesn't appear after building:
echo 1. Delete the old .exe files
echo 2. Rebuild using this script
echo 3. If still not showing, clear Windows icon cache:
echo    - Close File Explorer
echo    - Run: ie4uinit.exe -show
echo    - Or restart your computer
echo.
echo See ZEROTIER_SETUP_GUIDE.md for complete setup instructions.
echo.
pause
