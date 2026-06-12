[README.md](https://github.com/user-attachments/files/28874072/README.2.md)
# 📁 File Automator — Web Edition

A full-stack file automation system with a cyberpunk web UI, Flask REST API, and Python automation engine.
Now configured with `vercel.json` and a `/tmp` bypass to be deployable on Vercel.

## 🌌 Project Overview

The *File Automator* is designed to process batches of unorganized files instantly. It leverages a secure, session-based architecture where users upload files (up to a 50MB batch limit), execute isolated system operations, monitor live terminal logs and visual file trees, and download the neatly packaged results as a compressed .zip archive.

### ⚡ Core Operations

1. *Smart Extension Sorting (sort)* Automatically scans incoming files and moves them into categorized sub-folders based on their extensions. Mixed assets are instantly filed away into clean directories like /Images, /Documents, /Code, /Data, /Audio, and /Archives.
   
2. *Deep Memory Cleaning (clean)* Scans the targeted directory for redundant data. It filters out empty files containing exactly 0 bytes, permanently removing them to optimize disk space and eradicate clutter.

3. *Cryptographic Timestamping (rename)* Appends a standardized chronological timestamp (YYYYMMDD_HHMMSS_) to the front of every file name. This prevents filename collisions, fixes duplicates, and builds a clear audit trail. It is built intelligently to automatically skip files that are already stamped.

---

## 🛠️ Technical Architecture & Stack

The codebase is strictly modularized, splitting responsibilities cleanly between the interactive visual interface, server-side route handling, and the background system automation worker.

### 1. Visual Frontend (User Interface)
* *HTML5 & CSS3:* Crafted into a standalone, single-page reactive application styled with a custom dark-mode "Cyberpunk/Sci-Fi" aesthetic. Uses neon glowing boundaries, CSS Grid layouts, and specific typography (Orbitron, Rajdhani, Share Tech Mono).
* *Vanilla JavaScript (Fetch API):* Implements advanced drag-and-drop file ingestion, asynchronous non-blocking API interactions (preventing screen reloads), and handles real-time visual updates for operational counters, system log streams, and interactive tree graphs.

### 2. Backend Server (app.py)
* *Python & Flask:* Exposes the underlying python engine through a collection of lightweight RESTful endpoints.
* *Session Isolation Framework:* Uses secure, randomized UUID generation (SESSION_ID) to dynamically create segregated server directories (/uploads, /logs, /reports) per user session, ensuring multi-user security.
* *Memory-Optimized Zip Compression:* Uses Python's zipfile and io byte-streams to dynamically package processed folder trees into compressed archives directly inside RAM buffers, ensuring fast responses without caching junk data on the server.

### 3. Core Automation Engine (automator.py)
* *pathlib & os:* Native system integration to perform low-level, high-speed directory traversals, validity checks, and file property evaluations.
* *shutil:* Handles safe, reliable file shifting and high-level file tracking.
* *logging:* Implements highly granular logging handlers that stream raw execution details into distinct operational files simultaneously.
