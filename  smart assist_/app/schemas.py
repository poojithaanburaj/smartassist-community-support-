from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Literal

Category = Literal["food", "shelter", "medical", "other"]
Status = Literal["pending_verification", "verified", "assigned", "in_progress", "resolved", "rejected"]

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["citizen", "field_worker", "ngo", "admin"] = "citizen"

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ReportIn(BaseModel):
    reporter_name: str = Field(default="Anonymous", max_length=120)
    reporter_contact: str = Field(default="", max_length=80)
    description: str = Field(min_length=8, max_length=5000)
    location_text: str = Field(default="", max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

class VerifyIn(BaseModel):
    approved: bool

class AssignIn(BaseModel):
    ngo_id: int
    assigned_worker: str = Field(default="", max_length=120)

class StatusIn(BaseModel):
    status: Status
    note: str = Field(default="", max_length=1000)

class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_code: str
    reporter_name: str
    description: str
    category: str
    urgency: str
    ai_summary: str
    latitude: float | None
    longitude: float | None
    location_text: str
    status: str
    ngo_id: int | None
    assigned_worker: str
    created_at: str | None = None
