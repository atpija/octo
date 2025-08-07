#!/bin/bash
# server/build_installer.sh

APP_NAME="remotecompute-server"
VERSION="0.1"
BUILD_DIR="build"
INSTALL_DIR="$BUILD_DIR/usr/local/bin"
DEB_DIR="$BUILD_DIR/DEBIAN"

mkdir -p "$INSTALL_DIR" "$DEB_DIR"

# Konvertiere beide Skripte
pyinstaller --onefile server.py --name remotecompute-server
pyinstaller --onefile runner.py --name remotecompute-runner

mv dist/remotecompute-server "$INSTALL_DIR/"
mv dist/remotecompute-runner "$INSTALL_DIR/"

# DEBIAN/control Datei
cat > "$DEB_DIR/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3
Maintainer: DeinName
Description: Remote Compute Server + Runner
EOF

dpkg-deb --build "$BUILD_DIR" "${APP_NAME}_${VERSION}_amd64.deb"
echo "✅ Server Installer gebaut: ${APP_NAME}_${VERSION}_amd64.deb"
