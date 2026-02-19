#!/bin/bash

# Build script for File Renamer macOS application using PyInstaller (PySide6 UI)

set -euo pipefail

echo "Building File Renamer (PyInstaller, PySide6 UI)..."

# Show Python details
echo "Python: $(command -v python3)"
python3 --version || true

# Verify PySide6 import works
echo "Checking PySide6 availability..."
if ! python3 - <<'PY'
try:
    import PySide6  # noqa: F401
    print("PySide6 OK")
except Exception as e:
    print("PySide6 check failed:", e)
    raise
PY
then
  echo "PySide6 not available. Installing requirements..."
  pip3 install -r requirements.txt
fi

# Ensure icon.icns exists (generate from icon.png if missing)
ensure_icns() {
  if [ -f "icon.icns" ]; then
    echo "Icon file icon.icns exists."
    return
  fi
  if [ ! -f "icon.png" ]; then
    echo "ERROR: icon.png not found and icon.icns missing. Provide one of them."
    exit 1
  fi
  echo "Generating icon.icns from icon.png..."
  tmpset="icon.iconset"
  rm -rf "$tmpset" && mkdir -p "$tmpset"
  sips -z 16 16     icon.png --out "$tmpset/icon_16x16.png" >/dev/null
  sips -z 32 32     icon.png --out "$tmpset/icon_16x16@2x.png" >/dev/null
  sips -z 32 32     icon.png --out "$tmpset/icon_32x32.png" >/dev/null
  sips -z 64 64     icon.png --out "$tmpset/icon_32x32@2x.png" >/dev/null
  sips -z 128 128   icon.png --out "$tmpset/icon_128x128.png" >/dev/null
  sips -z 256 256   icon.png --out "$tmpset/icon_128x128@2x.png" >/dev/null
  sips -z 256 256   icon.png --out "$tmpset/icon_256x256.png" >/dev/null
  sips -z 512 512   icon.png --out "$tmpset/icon_256x256@2x.png" >/dev/null
  sips -z 512 512   icon.png --out "$tmpset/icon_512x512.png" >/dev/null
  sips -z 1024 1024 icon.png --out "$tmpset/icon_512x512@2x.png" >/dev/null
  iconutil -c icns "$tmpset" -o icon.icns
  rm -rf "$tmpset"
}

ensure_icns

# Clean previous build
rm -rf build dist __pycache__

# Build with PyInstaller
pyinstaller \
  --noconfirm \
  --windowed \
  --name "File Renamer" \
  --icon icon.icns \
  --add-data "icon.png:." \
  app_qt.py

# Result summary
if [ -d "dist/File Renamer.app" ]; then
  echo "✅ Build complete: dist/File Renamer.app"
  echo "To install: cp -R \"dist/File Renamer.app\" /Applications/"
  echo "First run: Right-click Open to bypass Gatekeeper for unsigned app"
else
  echo "❌ Build failed"
  exit 1
fi
