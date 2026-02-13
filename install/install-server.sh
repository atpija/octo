#!/bin/bash
set -e

VERSION="0.2.0"
BASE_URL="https://www.project-octo.com/download/v${VERSION}"

echo "Installing Octo Server v${VERSION}..."

# Datei herunterladen
curl -LO "$BASE_URL/octo-server_${VERSION}_amd64.deb"

# Paket installieren
sudo dpkg -i "octo-server_${VERSION}_amd64.deb"

# heruntergeladene Datei löschen
rm "octo-server_${VERSION}_amd64.deb"

echo "Octo Server installed."