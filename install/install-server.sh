#!/bin/bash
set -e

VERSION="0.2.0"
BASE_URL="https://github.com/atpija/octo/releases/download/v${VERSION}"

echo "Installing Octo Server v${VERSION}..."

curl -LO "$BASE_URL/octo-server_${VERSION}_amd64.deb"

sudo dpkg -i octo-server_${VERSION}_amd64.deb

rm octo-server_${VERSION}_amd64.deb

echo "Octo Server installed."