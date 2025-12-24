#!/usr/bin/env bash
set -e

echo "🔧 Installing Octo Server + Runner"

INPUT_DIR="$1"

# ------------------------------------------------------------
# Validierung
# ------------------------------------------------------------
if [ -z "$INPUT_DIR" ] || [ ! -d "$INPUT_DIR" ]; then
  echo "❌ No valid deb directory found"
  exit 1
fi

echo "📦 Using deb directory: $INPUT_DIR"
ls -lh "$INPUT_DIR"

# ------------------------------------------------------------
# Install
# ------------------------------------------------------------
sudo dpkg -i \
  "$INPUT_DIR"/octo-server*.deb \
  "$INPUT_DIR"/octo-runner*.deb \
  "$INPUT_DIR"/octo-client*.deb \
  || sudo apt-get -f install -y

# ------------------------------------------------------------
# Restart services (non-fatal)
# ------------------------------------------------------------
echo "🔁 Restarting services"
sudo systemctl restart octo-server || true
sudo systemctl restart octo-runner || true

echo "✅ Octo installation/update complete"
