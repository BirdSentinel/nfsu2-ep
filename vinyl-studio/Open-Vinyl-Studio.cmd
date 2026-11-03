@echo off
if exist "%~dp0..\Egyuttparkolas.exe" (
  start "" "%~dp0..\Egyuttparkolas.exe" --vinyl-studio
  exit /b
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Refresh-Decals.ps1"
if errorlevel 1 echo Could not refresh the library. Use the Load folder button in the browser.
start "" "%~dp0index.html"
