"""
tests/test_automator.py
=======================
pytest tests for the FileAutomator engine.
"""

import json
import pytest
from pathlib import Path
from automator import FileAutomator, setup_logging


@pytest.fixture
def tmp_dir(tmp_path):
    files = {
        "photo.jpg":   b"fake-image",
        "notes.txt":   b"hello world",
        "script.py":   b"print('hi')",
        "data.csv":    b"col1,col2\n1,2",
        "empty.log":   b"",
        "archive.zip": b"PK\x03\x04",
        "song.mp3":    b"ID3",
    }
    for name, content in files.items():
        (tmp_path / name).write_bytes(content)
    return tmp_path


@pytest.fixture
def logger(tmp_path):
    return setup_logging(str(tmp_path / "test.log"))


@pytest.fixture
def auto(tmp_dir, logger):
    return FileAutomator(str(tmp_dir), logger)


def test_validate_good(auto):
    assert auto.validate_directory() is True


def test_validate_missing(logger):
    fa = FileAutomator("/nonexistent/xyz", logger)
    assert fa.validate_directory() is False


def test_sort_creates_folders(auto, tmp_dir):
    auto.sort_by_extension()
    folders = {p.name for p in tmp_dir.iterdir() if p.is_dir()}
    assert "Images"   in folders
    assert "Code"     in folders
    assert "Data"     in folders
    assert "Archives" in folders
    assert "Audio"    in folders


def test_sort_no_loose_files(auto, tmp_dir):
    auto.sort_by_extension()
    loose = [p for p in tmp_dir.iterdir() if p.is_file()]
    assert loose == []


def test_clean_removes_empty(auto, tmp_dir):
    count = auto.clean_empty_files()
    assert count == 1
    assert not (tmp_dir / "empty.log").exists()


def test_clean_keeps_nonempty(auto, tmp_dir):
    auto.clean_empty_files()
    remaining = {p.name for p in tmp_dir.iterdir() if p.is_file()}
    assert "photo.jpg" in remaining
    assert "notes.txt" in remaining


def test_rename_adds_prefix(auto, tmp_dir):
    count = auto.rename_with_timestamps()
    assert count == 7
    for f in tmp_dir.iterdir():
        if f.is_file():
            assert f.name[:8].isdigit()


def test_rename_skips_stamped(auto, tmp_dir):
    auto.rename_with_timestamps()
    count2 = auto.rename_with_timestamps()
    assert count2 == 0


def test_report_export(auto, tmp_dir):
    auto.clean_empty_files()
    rp = str(tmp_dir / "report.json")
    auto.export_report(rp)
    with open(rp) as fh:
        data = json.load(fh)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all("operation" in e and "status" in e for e in data)
