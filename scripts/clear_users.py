"""Remove all registered users and profile uploads. Run from project root."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
USERS_DIR = DATA_DIR / "users"
UPLOADS_DIR = DATA_DIR / "uploads"
INDEX_FILE = USERS_DIR / "index.json"


def clear_all_users() -> int:
    if not DATA_DIR.exists():
        print("No data directory — nothing to clear.")
        return 0

    removed_users = 0
    USERS_DIR.mkdir(parents=True, exist_ok=True)
    for path in USERS_DIR.glob("*.json"):
        if path.name == "index.json":
            continue
        path.unlink(missing_ok=True)
        removed_users += 1

    INDEX_FILE.write_text("{}", encoding="utf-8")

    removed_uploads = 0
    if UPLOADS_DIR.exists():
        for child in UPLOADS_DIR.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
                removed_uploads += 1

    print(f"Cleared {removed_users} user file(s) and {removed_uploads} upload folder(s).")
    print(f"Reset {INDEX_FILE}")
    return removed_users


if __name__ == "__main__":
    if "--yes" not in sys.argv:
        print("This deletes ALL accounts and profile photos in data/users and data/uploads.")
        print("Re-run with --yes to confirm.")
        sys.exit(1)
    clear_all_users()
