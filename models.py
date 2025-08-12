from pydantic import BaseModel, Field, EmailStr
from typing import Optional

class ClassOut(BaseModel):
    id: int
    name: str
    instructor: str
    start_utc: str
    capacity: int
    available_slots: int


class BookRequest(BaseModel):
    class_id: int
    name: str = Field(..., min_length=2)
    email: EmailStr


class BookingOut(BaseModel):
    id: Optional[int] = None
    class_id: int
    class_name: str
    class_start_local: str  # Renamed for accuracy
    name: str
    email: str
    booked_at_utc: str  # Remains UTC