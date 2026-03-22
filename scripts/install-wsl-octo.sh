#!/usr/bin/env bash
set -e

DEB_DIR="$1/linux"

echo "Changing directory"
cd /mnt/c/actions-runner/_work/octo/octo

echo "Fix line endings"
sed -i 's/\r$//' scripts/install-octo.sh

echo "Make executable"
chmod +x scripts/install-octo.sh

echo "Run installer"
./scripts/install-octo.sh "$DEB_DIR"
