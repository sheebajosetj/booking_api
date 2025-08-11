"""
Seed three classes (Yoga, Zumba, HIIT) if classes table is empty.
Times are seeded as UTC strings.
"""
from datetime import datetime, timedelta
from databases_sql import list_classes, insert_class
from utils import utc_iso
import pytz


def seed_if_needed():
    classes = list_classes()
    if classes:
        return
    # We'll create three classes at sensible upcoming times (UTC)
    now = datetime.now(pytz.UTC)
    yoga_time = now + timedelta(days=1, hours=9)   # roughly tomorrow morning
    zumba_time = now + timedelta(days=1, hours=17) # tomorrow evening
    hiit_time = now + timedelta(days=2, hours=7)   # day after morning

    insert_class("Yoga", "Priya", utc_iso(yoga_time), 10)
    insert_class("Zumba", "Carlos", utc_iso(zumba_time), 15)
    insert_class("HIIT", "Aisha", utc_iso(hiit_time), 12)

