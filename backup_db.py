"""
backup_db.py — AptitudePro Database Backup Utility
====================================================
Run this BEFORE every deployment or code update:

    python backup_db.py

Creates a timestamped copy of the database in the /backups folder.
Safe to run while the app is stopped. Never deletes existing data.
"""

import os
import shutil
from datetime import datetime

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DB_PATH     = os.path.join(BASE_DIR, "instance", "aptipro.db")
BACKUP_DIR  = os.path.join(BASE_DIR, "backups")
# ─────────────────────────────────────────────────────────────────────────────

def backup():
    if not os.path.exists(DB_PATH):
        print(f"[BACKUP] No database found at {DB_PATH}. Nothing to back up.")
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"aptipro_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_name)

    shutil.copy2(DB_PATH, backup_path)
    size_kb = os.path.getsize(backup_path) // 1024

    print(f"[BACKUP] ✅ Database backed up successfully.")
    print(f"         Source : {DB_PATH}")
    print(f"         Backup : {backup_path}  ({size_kb} KB)")

    # ── Keep only the 10 most recent backups to save disk space ──────────────
    backups = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith("aptipro_") and f.endswith(".db")]
    )
    while len(backups) > 10:
        oldest = os.path.join(BACKUP_DIR, backups.pop(0))
        os.remove(oldest)
        print(f"[BACKUP] 🗑️  Removed old backup: {oldest}")

if __name__ == "__main__":
    backup()
