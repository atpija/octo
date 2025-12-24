#!/usr/bin/env bash
set -e

echo "🔧 Installing Octo Server + Runner"

DEB_DIR="$1"

if [ -z "$DEB_DIR" ]; then
  echo "❌ Usage: install-octo.sh <deb-directory>"
  exit 1
fi

if [ ! -d "$DEB_DIR" ]; then
  echo "❌ Deb directory not found: $DEB_DIR"
  exit 1
fi

sudo dpkg -i \
  "$DEB_DIR"/octo-server*.deb \
  "$DEB_DIR"/octo-runner*.deb \
  "$DEB_DIR"/octo-client*.deb \
  || sudo apt-get -f install -y

echo "🔁 Restarting services"
sudo systemctl restart octo-server || true
sudo systemctl restart octo-runner || true

echo "✅ Octo installation/update complete"
