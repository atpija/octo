$ErrorActionPreference = "Stop"
Write-Host "=== Building Octo Runner ==="

# Aufräumen
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }

# Build EXE
pyinstaller --onefile --icon=logo.ico runner.py --name octo-runner

# Build Installer
makensis installer_runner.nsi

Write-Host "[SUCCESS]" -ForegroundColor Green -NoNewline
Write-Host " Runner build completed!"

