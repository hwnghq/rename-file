# File Renamer - PySide6 + PyInstaller (macOS)

This document describes how to build and run the File Renamer app using a PySide6 UI and PyInstaller packaging.

## What changed vs. tkinter/py2app

- **GUI toolkit**: Switched from `tkinter` to `PySide6` (Qt), implemented in `app_qt.py`.
- **Packager**: Switched from `py2app` to `PyInstaller`.
- **Icon**: `icon.icns` is used as the app icon; the build script will generate it from `icon.png` if needed.

## Prerequisites

- macOS 12+
- Python 3.10+ (python.org build or Homebrew/pyenv both OK for PySide6)
- Command line tools that PyInstaller relies on (Xcode CLT suggested)

## Install dependencies

```bash
pip3 install -r requirements.txt
```

This installs:
- `PySide6` (Qt UI)
- `Pillow` (EXIF reading)
- `PyInstaller` (packaging)

## Build the .app bundle

Use the provided build script:

```bash
chmod +x build_app_pyinstaller.sh
./build_app_pyinstaller.sh
```

The script will:
- Verify PySide6 import
- Generate `icon.icns` from `icon.png` if missing
- Build `dist/File Renamer.app`

If successful, you’ll see:
```
✅ Build complete: dist/File Renamer.app
```

## Install to Applications and run from Launchpad

```bash
cp -R "dist/File Renamer.app" /Applications/
```

First run (unsigned app on macOS):
- Open Finder → Applications → right-click `File Renamer.app` → Open → confirm prompt.
- Subsequent launches work normally from Launchpad.

## Running without packaging (dev mode)

```bash
python3 app_qt.py
```

## Using the app

1. Click **Browse** to select a folder.
2. Click **Rename Files**.
3. The app renames video and image files to `yyyyMMdd_hhmmss_SSS.ext`.
4. Files already matching the format are skipped.
5. A completion dialog shows counts of renamed/skipped/errors.

## Notes

- Supported formats: MP4, MOV, AVI, MKV, WMV, FLV, WebM, M4V, 3GP, JPG, JPEG, PNG, GIF, BMP, TIFF, TIF, WebP, HEIC, HEIF.
- For images, the app tries EXIF `DateTimeOriginal`/`DateTime` first; then uses macOS birth time; then modification time.
- Filename conflicts get an incremental suffix (e.g., `_01`, `_02`, ...).

## Troubleshooting

- If build fails, ensure PyInstaller and PySide6 are installed and importable.
- If the app doesn’t start from Finder, try running the internal executable and check output:
  ```bash
  ./dist/File\ Renamer.app/Contents/MacOS/File\ Renamer
  ```
- If you need signing/notarization for distribution, consider using `codesign` and `notarytool` on the generated `.app`.
