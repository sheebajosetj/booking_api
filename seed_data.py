"""
Seed three classes (Yoga, Zumba, HIIT).
- Default: Adds missing classes only.
- --force: Resets all classes to new times + clears bookings.json.
Times are stored as UTC strings.
"""

import sys
import os
import json
from datetime import datetime, timedelta
from databases_sql import list_classes, insert_class
from utils import to_utc, IST

BOOKINGS_FILE = "bookings.json"

def clear_bookings():
    """Clear all bookings by emptying bookings.json."""
    if os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, "w") as f:
            json.dump([], f)
        print(f"Cleared all bookings in {BOOKINGS_FILE}")
    else:
        print(f"No {BOOKINGS_FILE} found, nothing to clear.")

def seed_classes(force=False):
    now_ist = datetime.now(IST)

    classes = [
        ("Yoga", (now_ist + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)),
        ("Zumba", (now_ist + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)),
        ("HIIT", (now_ist + timedelta(days=2)).replace(hour=7, minute=0, second=0, microsecond=0)),
    ]

    existing_names = {c["name"] for c in list_classes()}

    if force:
        clear_bookings()

    for name, ist_time in classes:
        if force or name not in existing_names:
            utc_time = to_utc(ist_time)
            insert_class(name, "Instructor", utc_time.isoformat(), 15)
            print(f"Seeded: {name} at {ist_time.strftime('%d %b %Y, %I:%M %p')} IST")

if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    seed_classes(force=force_flag)
