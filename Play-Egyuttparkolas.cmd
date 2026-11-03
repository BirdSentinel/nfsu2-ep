@echo off
set "GAME=%~dp0out\portable\Egyuttparkolas\Egyuttparkolas.exe"
if exist "%GAME%" (
    start "" "%GAME%"
    exit /b 0
)
echo The standalone game has not been packaged yet.
echo See docs\web\PORTABLE.md and run desktop\build-portable.ps1 first.
pause
exit /b 1
