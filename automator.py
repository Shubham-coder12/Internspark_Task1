"""
automator.py
============
Core file automation engine – framework-agnostic, importable by both
the CLI (cli.py) and the Flask web app (app.py).
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path


# ── Logging factory ──────────────────────────────────────────────────────────

def setup_logging(log_path: str = "automation.log") -> logging.Logger:
    """
    Return a logger that writes DEBUG+ to *log_path* and INFO+ to stdout.
    Each call creates a uniquely-named logger so Flask sessions don't clash.
    """
    name   = f"FileAutomator.{Path(log_path).stem}"
    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers on repeated calls
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


# ── FileAutomator ────────────────────────────────────────────────────────────

class FileAutomator:
    """
    Handles sort, clean, and rename operations on a target directory.

    Attributes
    ----------
    directory : Path
    logger    : Logger
    report    : list[dict]  – JSON-serialisable; ready for Pandas / Flask
    """

    EXTENSION_MAP: dict[str, str] = {
        ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
        ".txt": "Documents", ".md": "Documents",  ".odt": "Documents",
        ".ppt": "Documents", ".pptx": "Documents",
        ".csv": "Data",      ".xlsx": "Data",      ".xls": "Data",
        ".json": "Data",     ".xml": "Data",        ".yaml": "Data",
        ".yml": "Data",      ".sql": "Data",
        ".jpg": "Images",    ".jpeg": "Images",     ".png": "Images",
        ".gif": "Images",    ".bmp": "Images",      ".svg": "Images",
        ".webp": "Images",   ".ico": "Images",
        ".mp3": "Audio",     ".wav": "Audio",       ".flac": "Audio",
        ".aac": "Audio",     ".ogg": "Audio",
        ".mp4": "Video",     ".mov": "Video",       ".avi": "Video",
        ".mkv": "Video",     ".webm": "Video",
        ".py": "Code",       ".js": "Code",         ".ts": "Code",
        ".html": "Code",     ".css": "Code",        ".java": "Code",
        ".cpp": "Code",      ".c": "Code",          ".go": "Code",
        ".rs": "Code",       ".php": "Code",        ".rb": "Code",
        ".zip": "Archives",  ".tar": "Archives",    ".gz": "Archives",
        ".rar": "Archives",  ".7z": "Archives",     ".bz2": "Archives",
    }

    def __init__(self, directory: str, logger: logging.Logger):
        self.directory = Path(directory).resolve()
        self.logger    = logger
        self.report: list[dict] = []

    # ── Validation ─────────────────────────────────

    def validate_directory(self) -> bool:
        if not self.directory.exists():
            self.logger.error("Directory not found: %s", self.directory)
            return False
        if not self.directory.is_dir():
            self.logger.error("Not a directory: %s", self.directory)
            return False
        if not os.access(self.directory, os.R_OK | os.W_OK):
            self.logger.error("No read/write access: %s", self.directory)
            return False
        return True

    # ── Internals ──────────────────────────────────

    def _record(self, operation: str, src: str, dst: str = "",
                status: str = "OK", note: str = "") -> None:
        self.report.append({
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "operation": operation,
            "source":    src,
            "destination": dst,
            "status":    status,
            "note":      note,
        })

    def _iter_files(self) -> list[Path]:
        try:
            return [p for p in self.directory.iterdir() if p.is_file()]
        except PermissionError as exc:
            self.logger.error("Permission denied listing dir: %s", exc)
            return []

    # ── Operation 1: Sort ──────────────────────────

    def sort_by_extension(self) -> int:
        self.logger.info("START: Sort by Extension  [%s]", self.directory)
        count = 0
        for file in self._iter_files():
            ext         = file.suffix.lower()
            folder_name = self.EXTENSION_MAP.get(ext, "Misc")
            dest_folder = self.directory / folder_name
            try:
                dest_folder.mkdir(exist_ok=True)
                dest_path = dest_folder / file.name
                if dest_path.exists():
                    ts        = datetime.now().strftime("%H%M%S%f")
                    dest_path = dest_folder / f"{file.stem}_{ts}{file.suffix}"
                shutil.move(str(file), str(dest_path))
                self.logger.info("Sorted: %s → %s/", file.name, folder_name)
                self._record("sort", str(file), str(dest_path))
                count += 1
            except PermissionError:
                self.logger.error("Permission denied: %s", file.name)
                self._record("sort", str(file), status="ERROR",
                             note="PermissionError")
            except (shutil.Error, OSError) as exc:
                self.logger.error("Error sorting %s: %s", file.name, exc)
                self._record("sort", str(file), status="ERROR", note=str(exc))
        self.logger.info("END: Sorted %d file(s)", count)
        return count

    # ── Operation 2: Clean ─────────────────────────

    def clean_empty_files(self) -> int:
        self.logger.info("START: Clean Empty Files  [%s]", self.directory)
        count = 0
        for file in self._iter_files():
            try:
                size = file.stat().st_size
                if size == 0:
                    file.unlink()
                    self.logger.info("Deleted empty: %s", file.name)
                    self._record("clean", str(file), note="0-byte deleted")
                    count += 1
                else:
                    self.logger.debug("Kept (%d B): %s", size, file.name)
            except PermissionError:
                self.logger.error("Permission denied: %s", file.name)
                self._record("clean", str(file), status="ERROR",
                             note="PermissionError")
            except OSError as exc:
                self.logger.error("OS error %s: %s", file.name, exc)
                self._record("clean", str(file), status="ERROR", note=str(exc))
        self.logger.info("END: Cleaned %d file(s)", count)
        return count

    # ── Operation 3: Rename ────────────────────────

    def rename_with_timestamps(self) -> int:
        self.logger.info("START: Rename with Timestamps  [%s]", self.directory)
        count = 0
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        for file in self._iter_files():
            if len(file.name) >= 16 and file.name[:8].isdigit() and file.name[8] == "_":
                self.logger.warning("Already stamped, skipped: %s", file.name)
                self._record("rename", str(file), note="skipped-already-stamped")
                continue
            new_name = f"{ts}_{file.name}"
            new_path = self.directory / new_name
            try:
                file.rename(new_path)
                self.logger.info("Renamed: %s → %s", file.name, new_name)
                self._record("rename", str(file), str(new_path))
                count += 1
            except PermissionError:
                self.logger.error("Permission denied: %s", file.name)
                self._record("rename", str(file), status="ERROR",
                             note="PermissionError")
            except OSError as exc:
                self.logger.error("OS error %s: %s", file.name, exc)
                self._record("rename", str(file), status="ERROR", note=str(exc))
        self.logger.info("END: Renamed %d file(s)", count)
        return count

    # ── Export ─────────────────────────────────────

    def export_report(self, output_path: str = "report.json") -> None:
        try:
            with open(output_path, "w", encoding="utf-8") as fh:
                json.dump(self.report, fh, indent=2)
            self.logger.info("Report → %s (%d entries)",
                             output_path, len(self.report))
        except OSError as exc:
            self.logger.error("Report write failed: %s", exc)
