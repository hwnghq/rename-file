#!/usr/bin/env python3
"""
File Renamer - macOS Desktop Application (PySide6)
Renames video and image files based on their creation time in format: yyyyMMdd_hhmmss_SSS
"""

import os
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS
from PySide6.QtCore import QObject, QSettings, Qt, QThread, Signal, Slot
from PySide6.QtGui import QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

SUPPORTED_EXTENSIONS = {
    # Video formats
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".3gp",
    # Image formats
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".heic",
    ".heif",
}

TARGET_PATTERN = re.compile(
    r"^\d{8}_\d{6}_\d{3}\.(jpg|jpeg|png|gif|bmp|tiff|tif|webp|heic|heif|mp4|mov|avi|mkv|wmv|flv|webm|m4v|3gp)$",
    re.IGNORECASE,
)


def is_already_renamed(filename: str) -> bool:
    return bool(TARGET_PATTERN.match(filename))


def get_creation_time(file_path: Path, log_cb=None):
    """Get the creation time of a file using EXIF (for images) or filesystem metadata.
    Returns a datetime or None.
    """
    try:
        # Try EXIF for common image formats
        if file_path.suffix.lower() in {".jpg", ".jpeg", ".tiff", ".tif"}:
            try:
                with Image.open(file_path) as img:
                    exif_data = getattr(img, "_getexif", lambda: None)()
                    if exif_data:
                        for tag, value in exif_data.items():
                            tag_name = TAGS.get(tag, tag)
                            if tag_name in ("DateTimeOriginal", "DateTime"):
                                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
            except Exception as ex:
                if log_cb:
                    log_cb(f"EXIF read failed for {file_path.name}: {ex}")

        # Filesystem metadata
        stat = file_path.stat()

        # Birth time on macOS
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["stat", "-f", "%B", str(file_path)], capture_output=True, text=True
                )
                if result.returncode == 0:
                    birth_time = float(result.stdout.strip())
                    return datetime.fromtimestamp(birth_time)
            except Exception as ex:
                if log_cb:
                    log_cb(f"stat birth time failed for {file_path.name}: {ex}")

        # Fallback: modification time
        return datetime.fromtimestamp(stat.st_mtime)

    except Exception as e:
        if log_cb:
            log_cb(f"Error getting creation time for {file_path.name}: {e}")
        return None


class RenamerWorker(QObject):
    progress = Signal(int, int)  # current, total
    log = Signal(str)
    finished = Signal(int, int, int, int)  # renamed, skipped, errors, total

    def __init__(self, folder: Path):
        super().__init__()
        self.folder = folder
        self._abort = False

    @Slot()
    def run(self):
        try:
            if not self.folder.exists():
                self.log.emit("Selected folder does not exist!")
                self.finished.emit(0, 0, 1, 0)
                return

            # Collect files (case-insensitive)
            all_files = []
            for ext in SUPPORTED_EXTENSIONS:
                all_files.extend(self.folder.rglob(f"*{ext}"))
                all_files.extend(self.folder.rglob(f"*{ext.upper()}"))

            total = len(all_files)
            if total == 0:
                self.log.emit(
                    "No supported video or image files found in the selected folder!"
                )
                self.finished.emit(0, 0, 0, 0)
                return

            self.log.emit(f"Found {total} supported files")

            renamed = 0
            skipped = 0
            errors = 0

            for idx, file_path in enumerate(all_files, start=1):
                if self._abort:
                    break

                try:
                    self.progress.emit(idx, total)

                    if is_already_renamed(file_path.name):
                        skipped += 1
                        continue

                    creation_time = get_creation_time(file_path, self.log.emit)
                    if not creation_time:
                        self.log.emit(
                            f"Error: Could not get creation time for {file_path.name}"
                        )
                        errors += 1
                        continue

                    milliseconds = creation_time.microsecond // 1000
                    new_name = f"{creation_time.strftime('%Y%m%d_%H%M%S')}_{milliseconds:03d}{file_path.suffix.lower()}"
                    new_path = file_path.parent / new_name

                    counter = 1
                    original_new_path = new_path
                    while new_path.exists() and new_path != file_path:
                        name_without_ext = original_new_path.stem
                        new_name = f"{name_without_ext}_{counter:02d}{file_path.suffix.lower()}"
                        new_path = file_path.parent / new_name
                        counter += 1

                    if new_path != file_path:
                        file_path.rename(new_path)
                        self.log.emit(f"Renamed: {file_path.name} → {new_path.name}")
                        renamed += 1
                    else:
                        skipped += 1

                except Exception as e:
                    self.log.emit(f"Error processing {file_path.name}: {e}")
                    errors += 1

            self.finished.emit(renamed, skipped, errors, total)

        except Exception as e:
            self.log.emit(f"Unexpected error: {e}")
            self.finished.emit(0, 0, 1, 0)

    def abort(self):
        self._abort = True


class FileRenamerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Renamer")
        self.setMinimumSize(700, 480)
        if Path("icon.png").exists():
            self.setWindowIcon(QIcon("icon.png"))
        elif Path("icon.icns").exists():
            self.setWindowIcon(QIcon("icon.icns"))

        # Settings for persisting last used folder
        self.settings = QSettings("Cascade", "File Renamer")

        self.folder_edit = QLineEdit()
        self.folder_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.on_browse)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.addWidget(QLabel("Select Folder:"))
        top_row.addWidget(self.folder_edit)
        top_row.addWidget(browse_btn)

        self.progress = QProgressBar()
        self.status_label = QLabel("Ready to rename files")

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(8)
        self.rename_btn = QPushButton("Rename Files")
        self.rename_btn.setEnabled(False)
        self.rename_btn.clicked.connect(self.on_rename)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.on_cancel)
        # Make buttons small and add subtle border
        self.rename_btn.setFixedHeight(22)
        self.cancel_btn.setFixedHeight(22)
        base_btn_style = (
            "QPushButton {"
            "  background: transparent;"
            "  border: 1px solid #C0C0C0;"
            "  padding: 2px 8px;"
            "  border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            "  background: rgba(0,0,0,0.03);"
            "}"
            "QPushButton:pressed {"
            "  background: rgba(0,0,0,0.08);"
            "}"
            "QPushButton:disabled {"
            "  background: transparent;"
            "  color: palette(mid);"
            "  border-color: #E0E0E0;"
            "}"
        )
        self.rename_btn.setStyleSheet(base_btn_style)
        self.cancel_btn.setStyleSheet(base_btn_style)
        # Align buttons to the right
        buttons_row.addStretch(1)
        buttons_row.addWidget(self.rename_btn)
        buttons_row.addWidget(self.cancel_btn)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addLayout(top_row)
        layout.addWidget(self.progress)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons_row)
        layout.addWidget(log_group)

        # Thread/worker placeholders
        self.thread: QThread | None = None
        self.worker: RenamerWorker | None = None

        # Restore last folder if available
        last_folder = self.settings.value("last_folder", "")
        if isinstance(last_folder, str) and last_folder:
            p = Path(last_folder)
            if p.exists():
                self.folder_edit.setText(last_folder)
                self.rename_btn.setEnabled(True)
                self.append_log(f"Restored last folder: {last_folder}")

    def append_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.ensureCursorVisible()

    @Slot()
    def on_browse(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder containing files to rename"
        )
        if folder:
            self.folder_edit.setText(folder)
            self.rename_btn.setEnabled(True)
            self.append_log(f"Selected folder: {folder}")
            # Persist last folder
            self.settings.setValue("last_folder", folder)

    @Slot()
    def on_rename(self):
        folder_path = Path(self.folder_edit.text())
        if not folder_path.exists():
            QMessageBox.critical(self, "Error", "Selected folder does not exist!")
            return

        # Prepare worker and thread
        self.thread = QThread(self)
        self.worker = RenamerWorker(folder_path)
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # UI state
        self.rename_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.append_log("Starting renaming...")

        # Start
        self.thread.start()

    @Slot(int, int)
    def on_progress(self, current: int, total: int):
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(current)
        self.status_label.setText(f"Processing {current}/{total}")

    @Slot(int, int, int, int)
    def on_finished(self, renamed: int, skipped: int, errors: int, total: int):
        self.rename_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_label.setText("Renaming completed!")

        # Log summary directly in the app window instead of a popup
        self.append_log("File renaming completed!")
        self.append_log(f"Files renamed: {renamed}")
        self.append_log(f"Files skipped: {skipped}")
        if errors > 0:
            self.append_log(f"Errors: {errors}")
        self.append_log(f"Total files processed: {total}")

    @Slot()
    def on_cancel(self):
        if self.worker:
            self.worker.abort()
            self.append_log("Cancellation requested...")
            self.cancel_btn.setEnabled(False)


def main():
    app = QApplication([])
    window = FileRenamerWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
