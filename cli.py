"""
cli.py
======
Standalone CLI interface that reuses the FileAutomator engine.
"""

import argparse
from datetime import datetime
from pathlib import Path

from automator import FileAutomator, setup_logging

MENU = """
╔════════════════════════════════════╗
║      FILE AUTOMATOR  v1.0.0        ║
╠════════════════════════════════════╣
║  sort    – Sort by extension       ║
║  clean   – Delete empty files      ║
║  rename  – Add timestamp prefix    ║
╚════════════════════════════════════╝
"""

def parse_args():
    p = argparse.ArgumentParser(prog="file_automator")
    p.add_argument("-d", "--directory", default=None)
    p.add_argument("-o", "--operation",
                   choices=["sort", "clean", "rename"], default=None)
    p.add_argument("--log",    default="automation.log")
    p.add_argument("--report", default="report.json")
    return p.parse_args()


def main():
    args   = parse_args()
    logger = setup_logging(args.log)

    logger.info("Session started")
    print(MENU)

    directory = args.directory or input("Target directory path: ").strip()
    operation = args.operation or input("Operation (sort / clean / rename): ").strip()

    if operation not in ("sort", "clean", "rename"):
        print(f"[ERROR] Unknown operation '{operation}'")
        return

    automator = FileAutomator(directory, logger)
    if not automator.validate_directory():
        print("[ERROR] Cannot access directory.")
        return

    start = datetime.now()

    if operation == "sort":
        n = automator.sort_by_extension()
        print(f"\n✔  Sorted {n} file(s).")
    elif operation == "clean":
        n = automator.clean_empty_files()
        print(f"\n✔  Deleted {n} empty file(s).")
    else:
        n = automator.rename_with_timestamps()
        print(f"\n✔  Renamed {n} file(s).")

    elapsed = (datetime.now() - start).total_seconds()
    logger.info("Done in %.2fs", elapsed)
    automator.export_report(args.report)
    print(f"   Log    → {args.log}")
    print(f"   Report → {args.report}\n")


if __name__ == "__main__":
    main()
