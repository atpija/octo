#!/bin/bash
# client/build_installer.sh

APP_NAME="remotecompute-client"
VERSION="0.1"
BUILD_DIR="build"
INSTALL_DIR="$BUILD_DIR/usr/local/bin"
DEB_DIR="$BUILD_DIR/DEBIAN"

mkdir -p "$INSTALL_DIR" "$DEB_DIR"

# Konvertiere zu ausführbarer Datei
pyinstaller --onefile rc.py --name rc
mv dist/rc "$INSTALL_DIR/rc"

# DEBIAN/control Datei
cat > "$DEB_DIR/control" <<EOF
Package: $APP_NAME
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Depends: python3
Maintainer: DeinName
Description: Remote Compute Client CLI
EOF

dpkg-deb --build "$BUILD_DIR" "${APP_NAME}_${VERSION}_amd64.deb"
echo "✅ Client Installer gebaut: ${APP_NAME}_${VERSION}_amd64.deb"
