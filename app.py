"""
app.py  –  File Automator Web Interface (Vercel Edition)
========================================================
Flask application modified to run on Vercel's Serverless environment.
"""

import io
import json
import logging
import os
import shutil
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from flask import (Flask, jsonify, render_template, request,
                   send_file, send_from_directory)

from automator import FileAutomator, setup_logging

# ── App bootstrap ────────────────────────────────────────────────────────────

# VERCEL FIX: Use /tmp for writable storage in serverless environments.
# Vercel's file system is strictly read-only everywhere except the /tmp folder.
if os.environ.get("VERCEL") or os.environ.get("VERCEL_ENV"):
    BASE_DIR = Path("/tmp")
else:
    BASE_DIR = Path(__file__).parent

UPLOAD_DIR = BASE_DIR / "uploads"
LOG_DIR    = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"

for d in (UPLOAD_DIR, LOG_DIR, REPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# VERCEL FIX: Explicitly tell Flask where templates are, since Vercel might 
# execute the script from a different current working directory.
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024   # 50 MB total upload cap

# Root logger for the Flask app itself
flask_logger = setup_logging(str(LOG_DIR / "server.log"))


# ── Helpers ──────────────────────────────────────────────────────────────────

def session_dir(sid: str) -> Path:
    """Return (and create) the upload folder for a given session id."""
    p = UPLOAD_DIR / sid
    p.mkdir(parents=True, exist_ok=True)
    return p


def session_log(sid: str) -> Path:
    return LOG_DIR / f"{sid}.log"


def session_report(sid: str) -> Path:
    return REPORT_DIR / f"{sid}.json"


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/new-session", methods=["POST"])
def new_session():
    """Generate a fresh session id."""
    sid = uuid.uuid4().hex[:12]
    session_dir(sid)
    return jsonify({"session_id": sid})


@app.route("/api/upload", methods=["POST"])
def upload():
    """
    Accept multipart file uploads into the session folder.
    Body: form-data  { session_id: str, files: File[] }
    """
    sid = request.form.get("session_id", "").strip()
    if not sid:
        return jsonify({"error": "session_id is required"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    dest = session_dir(sid)
    saved = []
    for f in files:
        if f.filename:
            safe = Path(f.filename).name          # strip any path traversal
            f.save(dest / safe)
            saved.append(safe)

    flask_logger.info("[%s] Uploaded %d file(s): %s", sid, len(saved), saved)
    return jsonify({"session_id": sid, "uploaded": saved, "count": len(saved)})


@app.route("/api/run", methods=["POST"])
def run_operation():
    """
    Execute an automation operation on a session folder.
    Body (JSON): { session_id: str, operation: "sort"|"clean"|"rename" }
    """
    data = request.get_json(silent=True) or {}
    sid  = data.get("session_id", "").strip()
    op   = data.get("operation", "").strip()

    if not sid:
        return jsonify({"error": "session_id is required"}), 400
    if op not in ("sort", "clean", "rename"):
        return jsonify({"error": "operation must be sort | clean | rename"}), 400

    target = session_dir(sid)
    if not target.exists() or not any(target.iterdir()):
        return jsonify({"error": "Session folder is empty – upload files first. (Note: Vercel may have cleared the /tmp directory)"}), 400

    log_path    = str(session_log(sid))
    report_path = str(session_report(sid))
    logger      = setup_logging(log_path)

    automator = FileAutomator(str(target), logger)
    if not automator.validate_directory():
        return jsonify({"error": "Cannot access session directory"}), 500

    start = datetime.now()

    if op == "sort":
        count = automator.sort_by_extension()
        label = f"Sorted {count} file(s) into subfolders"
    elif op == "clean":
        count = automator.clean_empty_files()
        label = f"Deleted {count} empty file(s)"
    else:
        count = automator.rename_with_timestamps()
        label = f"Renamed {count} file(s) with timestamps"

    elapsed = round((datetime.now() - start).total_seconds(), 3)
    automator.export_report(report_path)

    # Build a simple folder snapshot for the UI
    snapshot = _folder_snapshot(target)

    flask_logger.info("[%s] %s in %.3fs", sid, label, elapsed)
    return jsonify({
        "session_id": sid,
        "operation":  op,
        "result":     label,
        "files":      count,
        "elapsed_s":  elapsed,
        "snapshot":   snapshot,
    })


@app.route("/api/report/<sid>")
def get_report(sid):
    """Return the JSON operation report for a session."""
    p = session_report(sid)
    if not p.exists():
        return jsonify({"entries": []})
    with open(p, encoding="utf-8") as fh:
        return jsonify({"entries": json.load(fh)})


@app.route("/api/log/<sid>")
def get_log(sid):
    """Return the last 100 lines of the session log."""
    p = session_log(sid)
    if not p.exists():
        return jsonify({"lines": []})
    with open(p, encoding="utf-8") as fh:
        lines = fh.readlines()
    return jsonify({"lines": [l.rstrip() for l in lines[-100:]]})


@app.route("/api/snapshot/<sid>")
def snapshot(sid):
    """Return the current file tree of a session folder."""
    target = session_dir(sid)
    return jsonify({"snapshot": _folder_snapshot(target)})


@app.route("/api/download/<sid>")
def download_zip(sid):
    """Stream the session folder as a ZIP archive."""
    target = session_dir(sid)
    if not target.exists():
        return jsonify({"error": "Session not found"}), 404

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in target.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(target))
    buf.seek(0)

    return send_file(
        buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"fileautomator_{sid}.zip",
    )


@app.route("/api/clear/<sid>", methods=["DELETE"])
def clear_session(sid):
    """Wipe all files in a session (keeps the folder)."""
    target = session_dir(sid)
    if target.exists():
        shutil.rmtree(target)
        target.mkdir()
    log = session_log(sid)
    rep = session_report(sid)
    for p in (log, rep):
        if p.exists():
            p.unlink()
    flask_logger.info("[%s] Session cleared", sid)
    return jsonify({"cleared": True})


# ── Internal helper ───────────────────────────────────────────────────────────

def _folder_snapshot(root: Path) -> list[dict]:
    """
    Walk a directory and return a JSON-serialisable tree.
    Each node: { name, path, type, size, children? }
    """
    def walk(p: Path) -> dict:
        if p.is_file():
            return {
                "name": p.name,
                "type": "file",
                "ext":  p.suffix.lower(),
                "size": p.stat().st_size,
            }
        children = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
        return {
            "name":     p.name,
            "type":     "dir",
            "children": [walk(c) for c in children],
        }

    if not root.exists():
        return []
    return [walk(c) for c in sorted(root.iterdir(), key=lambda x: (x.is_file(), x.name))]


# ── Dev server ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
