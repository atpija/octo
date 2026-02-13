#!/bin/bash
# server/build_installer.sh

APP_NAME="octo-server"
VERSION="0.2.0"
BUILD_DIR="build"
INSTALL_DIR="$BUILD_DIR/usr/local/bin"
DEB_DIR="$BUILD_DIR/DEBIAN"

# Alte Builds löschen
rm -rf "$BUILD_DIR" dist build

mkdir -p "$INSTALL_DIR" "$DEB_DIR"

# server.py zu ausführbarer Datei "octo-server"
pyinstaller --onefile server.py --name octo-server
mv dist/octo-server "$INSTALL_DIR/octo-server"

# DEBIAN/control Datei
cat > "$DEB_DIR/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3
Maintainer: Jan Pirringer
Description: Octo Remote Compute Server CLI
EOF

# Paket bauen
dpkg-deb --build "$BUILD_DIR" "${APP_NAME}_${VERSION}_amd64.deb"
echo -e "\033[0;32m[SUCCESS]\033[0m Server Installer gebaut: ${APP_NAME}_${VERSION}_amd64.deb"

