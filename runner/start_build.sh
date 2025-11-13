#!/bin/bash

# Install all required Python packages
echo "Installing required Python packages..."
pip install --upgrade pip setuptools wheel
pip install pyinstaller typer requests 

# Stelle sicher, dass build_installer.sh ausführbar ist
chmod +x build_installer.sh

# Starte das eigentliche Build-Skript
./build_installer.sh