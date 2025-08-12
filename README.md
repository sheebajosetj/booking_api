# Booking API (FastAPI) - Fitness Studio

## Setup
1. Create a folder `booking_api` and create the files from this repo inside it.
2. Create a virtualenv and install dependencies:

```bash
python -m venv env
source env/bin/activate   # macOS / Linux
# or on Windows (PowerShell)
# .\\env\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

3. Run the app

```bash
uvicorn main:app --reload
or 
python main.py
```

Open http://127.0.0.1:8000/docs to try it.

## Endpoints
- `GET /classes` - list upcoming classes. Optional query `tz` to view times in a timezone (e.g. `Asia/Kolkata`).
- `POST /book` - book a spot. JSON body: `{ "class_id": 1, "name": "Alice", "email": "a@example.com" }`
- `GET /bookings` - list bookings by email. Query param `email` required.

## Seed data
Seeded automatically when app first runs. Classes: Yoga, Zumba, HIIT.

## Example cURL
List classes in IST:
```bash
curl "http://127.0.0.1:8000/classes"
```
Book:
```bash
curl -X POST "http://127.0.0.1:8000/book" -H "Content-Type: application/json" -d '{"class_id":1,"name":"Sheeba","email":"sheeba@example.com"}'
```
Get bookings:
```bash
curl http://127.0.0.1:8000/bookings?email=john@example.com
```
