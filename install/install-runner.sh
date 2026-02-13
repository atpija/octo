#!/bin/bash
set -e

VERSION="0.2.0"
BASE_URL="https://www.project-octo.com/download/v${VERSION}"

echo "Installing Octo Runner v${VERSION}..."

# Datei herunterladen
curl -LO "$BASE_URL/octo-runner_${VERSION}_amd64.deb"

# Paket installieren
sudo dpkg -i "octo-runner_${VERSION}_amd64.deb"

# heruntergeladene Datei löschen
rm "octo-runner_${VERSION}_amd64.deb"

echo "Octo Runner installed."