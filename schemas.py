"""
Database Schemas for FacilityAI (Bookings + Communications)

Each Pydantic model maps to a MongoDB collection using the lowercase of the class name.
Example: class Customer -> collection "customer"
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

# Core entities
class Organization(BaseModel):
    name: str
    industry: Optional[str] = None
    timezone: str = Field(default="UTC")
    currency: str = Field(default="AUD")
    settings: dict = Field(default_factory=dict)

class Service(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int = Field(ge=5, le=480)
    price_cents: int = Field(ge=0)
    category: Optional[str] = None
    is_active: bool = True

class Staff(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    services: List[str] = Field(default_factory=list, description="IDs or names of services this staff can perform")
    timezone: Optional[str] = None
    is_active: bool = True

class Customer(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    marketing_opt_in: bool = False

class ScheduleSlot(BaseModel):
    service_id: Optional[str] = None
    staff_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    capacity: int = 1
    remaining: int = 1
    location: Optional[str] = None
    status: Literal["open", "held", "booked", "blocked"] = "open"

class Booking(BaseModel):
    customer_id: str
    service_id: str
    staff_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: Literal["pending", "confirmed", "cancelled"] = "confirmed"
    quantity: int = 1
    price_cents: int = 0
    source: Literal["phone", "web", "ai", "manual"] = "web"
    notes: Optional[str] = None
    schedule_slot_id: Optional[str] = None

class PaymentLink(BaseModel):
    customer_id: str
    amount_cents: int
    currency: str = "AUD"
    description: Optional[str] = None
    status: Literal["pending", "paid", "expired"] = "pending"
    token: Optional[str] = None
    url: Optional[str] = None
    expires_at: Optional[datetime] = None

class Transcript(BaseModel):
    call_id: str
    direction: Literal["inbound", "outbound"] = "inbound"
    text: str
    intent: Optional[str] = None
    summary: Optional[str] = None

# Minimal message log (email/SMS)
class Message(BaseModel):
    to: str
    channel: Literal["sms", "email"]
    subject: Optional[str] = None
    body: str
    status: Literal["queued", "sent", "failed"] = "queued"
    meta: dict = Field(default_factory=dict)
