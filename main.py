from fastapi import FastAPI, HTTPException, Query, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from typing import List
from datetime import datetime
import pytz
import logging
import json
from pathlib import Path
from contextlib import asynccontextmanager

# Local imports
from databases_sql import init_db, list_classes, get_class, count_bookings_for_class,count_bookings_by_email_for_class, count_total_bookings_by_email, create_booking
from seed_data import seed_classes
from models import BookingOut,BookRequest

# ---------- Config ----------
DATA_FILE = Path("bookings.json")
templates = Jinja2Templates(directory="templates")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("booking_api")

# ---------- App Lifecycle ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_classes
    logger.info("Database initialized and seeded.")
    yield
    logger.info("Application shutting down.")

app = FastAPI(title="Fitness Studio Booking API", lifespan=lifespan)


# ---------- File Helpers ----------
def _load_bookings():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def _save_bookings(bookings):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(bookings, f, indent=4)


# ---------- Core Booking Logic ----------
def process_booking(req):
    now_utc = datetime.now(pytz.UTC)

    # 1. Check if user already booked more than twice
    bookings = _load_bookings()
    email_bookings = [b for b in bookings if b["email"].lower() == req.email.lower()]
    if len(email_bookings) >= 2:
        raise HTTPException(status_code=400, detail="Booking failed – not allowed more than twice")

    # 2. Check class availability
    cls = get_class(req.class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")

    booked_count = count_bookings_for_class(req.class_id)
    if booked_count >= cls["capacity"]:
        raise HTTPException(status_code=400, detail="Booking failed – class is full")

    # 3. Save booking in DB
    booking_id = create_booking(
        req.class_id, req.name, req.email, now_utc.isoformat()
    )

    # 4. Save booking in JSON
    booking_data = req.dict()
    booking_data["booked_at"] = now_utc.isoformat()
    bookings.append(booking_data)
    _save_bookings(bookings)

    # 5. Calculate available slots
    available_slots = cls["capacity"] - booked_count - 1

    # 6. Return success response
    return {
        "booking_id": booking_id,
        "message": "Booking successful!",
        "available_slots": available_slots
    }
# ---------- API Endpoints ----------
@app.get("/classes")
def list_classes_api(timezone: str = Query('Asia/Kolkata')):
    try:
        target_tz = pytz.timezone(timezone)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    classes = []
    for cls in list_classes():
        class_start_utc = datetime.fromisoformat(cls["start_utc"].replace('Z', '+00:00'))
        local_start = class_start_utc.astimezone(target_tz)
        classes.append({
            "id": cls["id"],
            "name": cls["name"],
            "instructor": cls["instructor"],
            "start": local_start.strftime("%d %b %Y, %I:%M %p"),
            "capacity": cls["capacity"]
        })
    return classes


@app.post("/book")
def book_class_api(req: BookRequest):
    return process_booking(req)


@app.get("/bookings", response_model=List[BookingOut])
def get_bookings_api(email: str = Query(...), tz: str = Query("Asia/Kolkata")):
    try:
        target_tz = pytz.timezone(tz)
    except pytz.UnknownTimeZoneError:
        raise HTTPException(status_code=400, detail="Invalid timezone")

    bookings = [b for b in _load_bookings() if b["email"].lower() == email.lower()]
    out = []

    for b in bookings:
        cls = get_class(b["class_id"])
        utc_time = datetime.fromisoformat(cls["start_utc"].replace('Z', '+00:00'))
        local_time = utc_time.astimezone(target_tz)

        out.append(
            BookingOut(
                id=None,
                class_id=b["class_id"],
                class_name=cls["name"],
                class_start_local=local_time.strftime("%d %b %Y, %I:%M %p"),
                name=b["name"],
                email=b["email"],
                booked_at_utc=b["booked_at"]
            )
        )
    return out


# ---------- HTML Frontend ----------
@app.get("/", response_class=HTMLResponse)
def home(request: Request, tz: str = "Asia/Kolkata", message: str = None, status: str = None):
    try:
        target_tz = pytz.timezone(tz)
    except pytz.UnknownTimeZoneError:
        tz = "Asia/Kolkata"
        target_tz = pytz.timezone(tz)

    now_utc = datetime.now(pytz.UTC)
    classes_data = []

    for r in list_classes():
        class_start_utc = datetime.fromisoformat(r["start_utc"].replace('Z', '+00:00'))
        if class_start_utc < now_utc:
            continue
        local_start = class_start_utc.astimezone(target_tz)

        bookings = [b for b in _load_bookings() if b["class_id"] == r["id"]]
        available = max(0, r["capacity"] - len(bookings))

        classes_data.append({
            "id": r["id"],
            "name": r["name"],
            "instructor": r["instructor"],
            "start": local_start.strftime("%d %b %Y, %I:%M %p"),
            "available": available
        })

    classes_data.sort(key=lambda x: datetime.strptime(x["start"], "%d %b %Y, %I:%M %p"))

    return templates.TemplateResponse(
    "classes.html",
    {
        "request": request,
        "classes": classes_data,
        "current_tz": tz, 
        "message": message,
        "status": status,
        "now": datetime.now(target_tz).strftime("%d %b %Y, %I:%M %p") 
    }
)



@app.post("/book-form")
def book_spot_form(class_id: int = Form(...), name: str = Form(...), email: str = Form(...)):
    try:
        process_booking(BookRequest(class_id=class_id, name=name, email=email))
        return RedirectResponse(url=f"/?message=Booking+successful!&status=success", status_code=303)
    except HTTPException as e:
        return RedirectResponse(url=f"/?message={e.detail}&status=error", status_code=303)


# ---------- Jinja Filter ----------
def datetimeformat(value, format="%d %b %Y, %I:%M %p"):
    if isinstance(value, datetime):
        return value.strftime(format)
    return datetime.fromisoformat(value).strftime(format)

templates.env.filters["datetimeformat"] = datetimeformat


# ---------- Run ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
