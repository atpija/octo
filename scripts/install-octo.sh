#!/usr/bin/env bash
set -e

export DEBIAN_FRONTEND=noninteractive

echo "🔧 Installing Octo Server + Runner"

INPUT_DIR="$1"

if [ -z "$INPUT_DIR" ] || [ ! -d "$INPUT_DIR" ]; then
  echo "❌ No valid deb directory found"
  exit 1
fi

echo "📦 Using deb directory: $INPUT_DIR"
ls -lh "$INPUT_DIR"

echo "📦 Installing debs"
sudo -n dpkg -i \
  "$INPUT_DIR"/octo-server*.deb \
  "$INPUT_DIR"/octo-runner*.deb \
  || sudo -n apt-get -f install -y

echo "🔁 Restarting services"
sudo -n systemctl restart octo-server || true
sudo -n systemctl restart octo-runner || true

echo "✅ Octo installation/update complete"

echo "🚀 Enabling and starting services"
# Server starten
sudo systemctl enable --now octo-server

# Runner starten (Token-abhängig)
sudo systemctl enable --now octo-runner@demo-token
sudo systemctl enable --now octo-runner@demo-token1
sudo systemctl enable --now octo-runner@demo-token2

