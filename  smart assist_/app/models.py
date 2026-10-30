from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Float, Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="citizen")  # citizen, field_worker, ngo, admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class NGO(Base):
    __tablename__ = "ngos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    services: Mapped[str] = mapped_column(String(255))  # comma-separated categories
    address: Mapped[str] = mapped_column(String(255), default="")
    latitude: Mapped[float] = mapped_column(Float, default=11.0168)
    longitude: Mapped[float] = mapped_column(Float, default=76.9558)
    capacity: Mapped[int] = mapped_column(Integer, default=10)
    active_cases: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    contact: Mapped[str] = mapped_column(String(120), default="")

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    reporter_name: Mapped[str] = mapped_column(String(120), default="Anonymous")
    reporter_contact: Mapped[str] = mapped_column(String(80), default="")
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), index=True)
    urgency: Mapped[str] = mapped_column(String(20), default="normal")
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_text: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(30), default="pending_verification", index=True)
    verified_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    ngo_id: Mapped[int | None] = mapped_column(ForeignKey("ngos.id"), nullable=True)
    assigned_worker: Mapped[str] = mapped_column(String(120), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    ngo: Mapped[NGO | None] = relationship()
