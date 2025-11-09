#!/bin/bash
pip install pyinstaller
# Stelle sicher, dass build_installer.sh ausführbar ist
chmod +x build_installer.sh

# Starte das eigentliche Build-Skript
./build_installer.sh