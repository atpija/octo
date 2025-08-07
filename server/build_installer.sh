#!/bin/bash
set -e

APP_NAME="remotecompute-server"
VERSION="0.1"

# Temporäre Verzeichnisse
BUILD_DIR="build"
INSTALL_PREFIX="$BUILD_DIR/opt/remotecompute"
BIN_DIR="$INSTALL_PREFIX/bin"
DEBIAN_DIR="$BUILD_DIR/DEBIAN"

# Leere alte Builds
rm -rf "$BUILD_DIR" dist build __pycache__ *.spec

# Erstelle Verzeichnisse
mkdir -p "$BIN_DIR" "$DEBIAN_DIR"

# Baue Executables
pyinstaller --onefile server.py --name remotecompute-server
pyinstaller --onefile runner.py --name remotecompute-runner

# Kopiere Executables ins Paket
cp dist/remotecompute-server "$BIN_DIR/"
cp dist/remotecompute-runner "$BIN_DIR/"

# Kontroll-Datei
cat > "$DEBIAN_DIR/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3
Maintainer: Dein Name
Description: Remote Compute Server + Runner
EOF

# Baue das .deb
dpkg-deb --build "$BUILD_DIR" "${APP_NAME}_${VERSION}_amd64.deb"

echo "✅ Installer gebaut: ${APP_NAME}_${VERSION}_amd64.deb"

