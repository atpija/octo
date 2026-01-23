$ErrorActionPreference = "Stop"
Write-Host "=== Building Octo Server ==="

# Aufräumen
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }

# Build EXE
pyinstaller --onefile --icon=logo.ico server.py --name octo-server

# Build Installer
makensis installer_server.nsi

Write-Host "[SUCCESS]" -ForegroundColor Green -NoNewline
Write-Host " Server build completed!"

