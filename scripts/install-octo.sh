#!/usr/bin/env bash
set -e

echo "🔧 Installing Octo Server + Runner"

INPUT_DIR="$1"
DEB_DIR=""

# ------------------------------------------------------------
# 1️⃣ Wenn Pfad übergeben wurde und existiert → benutzen
# ------------------------------------------------------------
if [ -n "$INPUT_DIR" ] && [ -d "$INPUT_DIR" ]; then
  DEB_DIR="$INPUT_DIR"
fi

# ------------------------------------------------------------
# 2️⃣ Fallback: lokaler Artefact-Cache (/mnt/c/octo/artefacts/*)
# ------------------------------------------------------------
if [ -z "$DEB_DIR" ]; then
  echo "🔍 Searching in /mnt/c/octo/artefacts ..."
  DEB_DIR=$(ls -td /mnt/c/octo/artefacts/* 2>/dev/null | head -n 1 || true)
fi

# ------------------------------------------------------------
# 3️⃣ Fallback: Repo docker_debs/
# ------------------------------------------------------------
if [ -z "$DEB_DIR" ] && [ -d "./docker_debs" ]; then
  DEB_DIR="./docker_debs"
fi

# ------------------------------------------------------------
# 4️⃣ Validierung
# ------------------------------------------------------------
if [ -z "$DEB_DIR" ] || [ ! -d "$DEB_DIR" ]; then
  echo "❌ No valid deb directory found"
  exit 1
fi

echo "📦 Using deb directory: $DEB_DIR"
ls -lh "$DEB_DIR"

# ------------------------------------------------------------
# 5️⃣ Install
# ------------------------------------------------------------
sudo dpkg -i \
  "$DEB_DIR"/octo-server*.deb \
  "$DEB_DIR"/octo-runner*.deb \
  "$DEB_DIR"/octo-client*.deb \
  || sudo apt-get -f install -y

# ------------------------------------------------------------
# 6️⃣ Restart services (non-fatal)
# ------------------------------------------------------------
echo "🔁 Restarting services"
sudo systemctl restart octo-server || true
sudo systemctl restart octo-runner || true

echo "✅ Octo installation/update complete"
