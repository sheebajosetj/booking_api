from fastapi import FastAPI, HTTPException, Query, Request, Form
from typing import List
import logging
from datetime import datetime
import pytz
from contextlib import asynccontextmanager
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import json
from pathlib import Path
from pydantic import BaseModel, EmailStr
from utils import from_utc_iso_to_tz
from databases_sql import (
    init_db,
    list_classes,
    get_class
)
from seed_data import seed_if_needed
from models import ClassOut, BookingOut
from fastapi.templating import Jinja2Templates


# -----------------------------------
# App setup
# -----------------------------------
DATA_FILE = Path("bookings.json")
templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("booking_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_if_needed()
    logger.info("Database initialized and seed run (if needed).")
    yield
    logger.info("Application shutting down.")

app = FastAPI(
    title="Fitness Studio Booking API",
    lifespan=lifespan
)


# -----------------------------------
# Models
# -----------------------------------
class BookRequest(BaseModel):
    class_id: int
    name: str
    email: EmailStr


# -----------------------------------
# JSON API
# -----------------------------------
@app.get("/classes", response_model=List[ClassOut])
def get_classes_api(tz: str = Query("UTC", description="IANA timezone name, e.g. Asia/Kolkata")):
    """List upcoming classes in the requested timezone."""
    try:
        _ = pytz.timezone(tz)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    rows = list_classes()
    out = []
    now_utc = datetime.now(pytz.UTC)
    for r in rows:
        class_start = datetime.fromisoformat(r["start_utc"])
        if class_start.tzinfo is None:
            class_start = class_start.replace(tzinfo=pytz.UTC)
        if class_start < now_utc:
            continue

        booked = sum(1 for b in _load_bookings() if b["class_id"] == r["id"])
        available = max(0, r["capacity"] - booked)
        start_in_tz = from_utc_iso_to_tz(r["start_utc"], tz)

        out.append(
            ClassOut(
                id=r["id"],
                name=r["name"],
                instructor=r["instructor"],
                start_utc=start_in_tz,
                capacity=r["capacity"],
                available_slots=available,
            )
        )
    return out


@app.post("/book")
def book_class(req: BookRequest):
    """Book a spot and save in bookings.json (no DB)."""
    cls = get_class(req.class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    class_start = datetime.fromisoformat(cls["start_utc"])
    if class_start.tzinfo is None:
        class_start = class_start.replace(tzinfo=pytz.UTC)
    now_utc = datetime.now(pytz.UTC)
    if class_start < now_utc:
        raise HTTPException(status_code=400, detail="Cannot book past classes")

    bookings = _load_bookings()
    booked_count = sum(1 for b in bookings if b["class_id"] == req.class_id)
    if booked_count >= cls["capacity"]:
        raise HTTPException(status_code=409, detail="Class is full")

    booking_data = req.dict()
    booking_data["booked_at"] = now_utc.isoformat()
    bookings.append(booking_data)
    _save_bookings(bookings)

    available_slots = cls["capacity"] - booked_count - 1
    return {"message": "Booking successful!", "available_slots": available_slots}


@app.get("/bookings", response_model=List[BookingOut])
def get_bookings_api(
    email: str = Query(..., description="Email to fetch bookings for"),
    tz: str = Query("UTC", description="IANA timezone name")
):
    """Get bookings for an email from bookings.json."""
    try:
        _ = pytz.timezone(tz)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    bookings = [b for b in _load_bookings() if b["email"].lower() == email.lower()]
    out = []
    for b in bookings:
        cls = get_class(b["class_id"])
        start_in_tz = from_utc_iso_to_tz(cls["start_utc"], tz)
        out.append(
            BookingOut(
                id=None,
                class_id=b["class_id"],
                class_name=cls["name"],
                class_start_utc=start_in_tz,
                name=b["name"],
                email=b["email"],
                booked_at_utc=b["booked_at"],
            )
        )
    return out


# -----------------------------------
# HTML Frontend
# -----------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request, tz: str = "Asia/Kolkata", message: str = None):
    """Show upcoming classes with booking form in local time."""
    try:
        _ = pytz.timezone(tz)
    except Exception:
        tz = "UTC"  # fallback if invalid

    rows = list_classes()
    now_utc = datetime.now(pytz.UTC)
    classes_data = []

    for r in rows:
        class_start = datetime.fromisoformat(r["start_utc"])
        if class_start.tzinfo is None:
            class_start = class_start.replace(tzinfo=pytz.UTC)

        if class_start < now_utc:
            continue

        booked = sum(1 for b in _load_bookings() if b["class_id"] == r["id"])
        available = max(0, r["capacity"] - booked)

        if available > 0:
            classes_data.append({
                "id": r["id"],
                "name": r["name"],
                "instructor": r["instructor"],
                "start": from_utc_iso_to_tz(r["start_utc"], tz),
                "available": available
            })

    return templates.TemplateResponse(
        "classes.html",
        {"request": request, "classes": classes_data, "tz": tz, "message": message}
    )


@app.post("/book-form")
def book_spot_form(
    class_id: int = Form(...),
    name: str = Form(...),
    email: str = Form(...)
):
    """Handle HTML form booking and save to bookings.json."""
    try:
        book_class(BookRequest(class_id=class_id, name=name, email=email))
        msg = "Booking successful!"
    except HTTPException as e:
        msg = e.detail
    
    return RedirectResponse(url=f"/?message={msg}", status_code=303)



templates = Jinja2Templates(directory="templates")

def datetimeformat(value, format="%d %b %Y, %I:%M %p"):
    if isinstance(value, datetime):
        return value.strftime(format)
    return datetime.fromisoformat(value).strftime(format)

# ✅ Register the filter here
templates.env.filters["datetimeformat"] = datetimeformat



# -----------------------------------
# File storage helpers
# -----------------------------------
def _load_bookings():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_bookings(bookings):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, indent=4)


# -----------------------------------
# Entry point
# -----------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
