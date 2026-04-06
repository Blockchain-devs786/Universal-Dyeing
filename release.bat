@echo off
SETLOCAL EnableDelayedExpansion

:: Get current date and time for the commit message
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set commit_message=Release - %datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2% %datetime:~8,2%:%datetime:~10,2%

echo [1/3] Staging all changes...
git add .

echo [2/3] Committing changes...
git commit -m "!commit_message!"

echo [3/3] Pushing to GitHub...
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo SUCCESS: Code pushed to GitHub!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo ERROR: Push failed. Check your connection or git status.
    echo ========================================
)

pause
