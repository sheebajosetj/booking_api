from pydantic import BaseModel, Field, EmailStr


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
    id: int
    class_id: int
    class_name: str
    class_start_utc: str
    name: str
    email: str
    booked_at_utc: str
