#!/bin/bash
# client/build_installer.sh

APP_NAME="octo-client"
VERSION="0.2.1"
BUILD_DIR="build"
INSTALL_DIR="$BUILD_DIR/usr/local/bin"
DEB_DIR="$BUILD_DIR/DEBIAN"

# Vorherige Builds löschen
rm -rf "$BUILD_DIR" dist build

mkdir -p "$INSTALL_DIR" "$DEB_DIR"

# Konvertiere client.py zu ausführbarer Datei "octo"
pyinstaller --onefile client.py --name octo
mv dist/octo "$INSTALL_DIR/octo"

# DEBIAN/control Datei
cat > "$DEB_DIR/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3
Maintainer: Jan Pirringer
Description: Octo Remote Compute Client CLI
EOF

# Paket bauen
dpkg-deb --build "$BUILD_DIR" "${APP_NAME}_${VERSION}_amd64.deb"
echo -e "\033[0;32m[SUCCESS]\033[0m Client Installer gebaut: ${APP_NAME}_${VERSION}_amd64.deb"
