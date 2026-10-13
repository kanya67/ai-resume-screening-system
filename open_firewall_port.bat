@echo off
:: This script MUST be run as Administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator access...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit
)

echo ================================================
echo   AI Resume Screener - Phone Access Setup
echo ================================================
echo.

echo [1/2] Opening firewall port 5000...
netsh advfirewall firewall delete rule name="AI Resume Screener Port 5000" >nul 2>&1
netsh advfirewall firewall add rule name="AI Resume Screener Port 5000" dir=in action=allow protocol=TCP localport=5000
if %errorlevel% equ 0 (
    echo [OK] Port 5000 is now open!
) else (
    echo [ERROR] Failed to open port.
)

echo.
echo [2/2] Getting your PC's IP address...
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "169.254"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP: =%

echo.
echo ================================================
echo   SUCCESS! Phone Access is Ready
echo ================================================
echo.
echo   Open this URL on your phone:
echo.
echo     http://%IP%:5000
echo.
echo   Make sure your phone is on the SAME WiFi!
echo ================================================
echo.
pause
