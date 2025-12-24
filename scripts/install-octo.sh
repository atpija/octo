#!/usr/bin/env bash
set -e

echo "🔧 Installing Octo Server + Runner"

ROOT_DIR="$1"

if [ -z "$ROOT_DIR" ]; then
  echo "❌ Usage: install-octo.sh <artifact-root-dir>"
  exit 1
fi

if [ ! -d "$ROOT_DIR" ]; then
  echo "❌ Artifact root not found: $ROOT_DIR"
  exit 1
fi

echo "🔍 Searching in $ROOT_DIR ..."

# ------------------------------------------------------------
# Find directory containing octo-*.deb
# ------------------------------------------------------------
DEB_DIR=$(find "$ROOT_DIR" -type f -name 'octo-*.deb' -printf '%h\n' | sort -u | head -n 1)

if [ -z "$DEB_DIR" ]; then
  echo "❌ No octo-*.deb files found under $ROOT_DIR"
  exit 1
fi

echo "📦 Using deb directory: $DEB_DIR"
ls -lh "$DEB_DIR"

# ------------------------------------------------------------
# Install packages
# ------------------------------------------------------------
sudo dpkg -i \
  "$DEB_DIR"/octo-server*.deb \
  "$DEB_DIR"/octo-runner*.deb \
  "$DEB_DIR"/octo-client*.deb \
  || sudo apt-get -f install -y

# ------------------------------------------------------------
# Restart services
# ------------------------------------------------------------
echo "🔁 Restarting services"
sudo systemctl restart octo-server || true
sudo systemctl restart octo-runner || true

# ------------------------------------------------------------
# Verify
# ------------------------------------------------------------
echo "✅ Octo installation/update complete"
octo-server --version || true
octo-runner --version || true
octo --version || true
