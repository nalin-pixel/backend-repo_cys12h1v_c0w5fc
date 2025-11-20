import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from database import db, create_document, get_documents

app = FastAPI(title="FacilityAI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "FacilityAI backend is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# Lightweight availability search for AI assistant
class AvailabilityQuery(BaseModel):
    service_id: Optional[str] = None
    staff_id: Optional[str] = None
    date: Optional[str] = None  # YYYY-MM-DD
    days: int = 7
    limit: int = 20

@app.post("/api/availability")
def check_availability(query: AvailabilityQuery):
    filter_dict = {"status": "open"}
    if query.service_id:
        filter_dict["service_id"] = query.service_id
    if query.staff_id:
        filter_dict["staff_id"] = query.staff_id
    # date window
    if query.date:
        try:
            start_day = datetime.fromisoformat(query.date)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    else:
        start_day = datetime.utcnow()
    end_day = start_day + timedelta(days=query.days)
    filter_dict["start_time"] = {"$gte": start_day, "$lt": end_day}
    slots = get_documents("scheduleslot", filter_dict, limit=query.limit)
    # normalize ObjectId
    for s in slots:
        s["_id"] = str(s.get("_id"))
    return {"slots": slots}

# Create a booking quickly (AI or receptionist draft then confirm)
class BookingCreate(BaseModel):
    customer_id: str
    service_id: str
    staff_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    source: Optional[str] = "ai"

@app.post("/api/bookings")
def create_booking_api(payload: BookingCreate):
    # Optional: check slot exists/open
    slot = None
    slots = get_documents("scheduleslot", {"start_time": payload.start_time, "end_time": payload.end_time}, limit=1)
    if slots:
        slot = slots[0]
        if slot.get("status") != "open" or int(slot.get("remaining", 1)) <= 0:
            raise HTTPException(status_code=400, detail="Slot not available")
    booking = {
        "customer_id": payload.customer_id,
        "service_id": payload.service_id,
        "staff_id": payload.staff_id,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "status": "confirmed",
        "quantity": 1,
        "price_cents": 0,
        "source": payload.source or "ai",
        "notes": payload.notes,
        "schedule_slot_id": str(slot.get("_id")) if slot else None,
    }
    booking_id = create_document("booking", booking)
    # Reduce remaining if slot exists
    if slot:
        try:
            from bson import ObjectId
            db.scheduleslot.update_one({"_id": ObjectId(str(slot["_id"]))}, {"$inc": {"remaining": -1}, "$set": {"status": "booked" if int(slot.get("remaining",1)) -1 <=0 else "open"}})
        except Exception:
            pass
    return {"id": booking_id, "status": "created"}

# Payment link draft (stub, no processor integration)
class PaymentLinkCreate(BaseModel):
    customer_id: str
    amount_cents: int
    description: Optional[str] = None

@app.post("/api/payment-links")
def create_payment_link(payload: PaymentLinkCreate):
    # Create a simple tokenized link users can click to pay later (front-end will show a mock checkout)
    import secrets
    token = secrets.token_urlsafe(12)
    url = f"/pay/{token}"
    link = {
        "customer_id": payload.customer_id,
        "amount_cents": payload.amount_cents,
        "currency": "AUD",
        "description": payload.description,
        "status": "pending",
        "token": token,
        "url": url,
        "expires_at": datetime.utcnow() + timedelta(days=7)
    }
    link_id = create_document("paymentlink", link)
    return {"id": link_id, "token": token, "url": url}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
