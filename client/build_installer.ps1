$ErrorActionPreference = "Stop"
Write-Host "=== Building Octo Client ==="

# Aufräumen
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }

# Build EXE
pyinstaller --onefile --icon=logo.ico client.py --name octo

# Build Installer
makensis installer_client.nsi

Write-Host "[SUCCESS]" -ForegroundColor Green -NoNewline
Write-Host " Client build completed!"

