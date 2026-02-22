#!/bin/bash
set -e

BASE_URL="https://www.project-octo.com/download"

echo "Fetching latest Octo version..."

VERSION=$(curl -fsSL "$BASE_URL/latest.txt")

if [ -z "$VERSION" ]; then
    echo "Error: Could not determine latest version."
    exit 1
fi

PACKAGE="octo-server_${VERSION}_amd64.deb"
DOWNLOAD_URL="$BASE_URL/v${VERSION}/$PACKAGE"
HASH_URL="$DOWNLOAD_URL.sha256"

echo "Downloading $PACKAGE..."

curl -fL -o "$PACKAGE" "$DOWNLOAD_URL"
curl -fL -o "$PACKAGE.sha256" "$HASH_URL"

echo "Verifying package integrity..."

sha256sum -c "$PACKAGE.sha256"

echo "Installing..."

sudo dpkg -i "$PACKAGE"

rm "$PACKAGE" "$PACKAGE.sha256"

echo "Octo Server v${VERSION} installed successfully."
