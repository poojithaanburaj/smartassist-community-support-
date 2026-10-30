from contextlib import asynccontextmanager
from datetime import datetime, timezone
from math import radians, sin, cos, asin, sqrt
from uuid import uuid4
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from .database import Base, engine, get_db, SessionLocal
from .models import User, NGO, Case
from .schemas import RegisterIn, LoginIn, ReportIn, VerifyIn, AssignIn, StatusIn
from .security import hash_password, verify_password, create_token, current_user, require_roles
from .ai import classify_need, assess_urgency, summarize, duplicate_candidates

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(NGO).count() == 0:
            db.add_all([
                NGO(name="Coimbatore Community Kitchen", services="food,other", address="Coimbatore", latitude=11.0168, longitude=76.9558, capacity=30, active_cases=4, verified=True, contact="community@example.org"),
                NGO(name="Hope Shelter Network", services="shelter,food", address="Coimbatore", latitude=11.0250, longitude=76.9600, capacity=20, active_cases=3, verified=True, contact="shelter@example.org"),
                NGO(name="Community Health Support", services="medical,other", address="Coimbatore", latitude=11.0050, longitude=76.9700, capacity=15, active_cases=2, verified=True, contact="health@example.org"),
                NGO(name="Pending NGO Example", services="food,shelter", address="Coimbatore", latitude=11.02, longitude=76.94, capacity=10, active_cases=0, verified=False, contact=""),
            ])
            db.commit()
    finally:
        db.close()
    yield

app = FastAPI(title="SmartAssist API", description="Community assistance case management MVP", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def home():
    with open("static/index.html", encoding="utf-8") as f:
        return f.read()

@app.get("/api/health")
def health():
    return {"status": "ok", "project": "SmartAssist"}

@app.post("/api/auth/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Email is already registered")
    # Public registration cannot grant privileged roles.
    role = "citizen"
    user = User(name=data.name.strip(), email=data.email.lower(), password_hash=hash_password(data.password), role=role)
    db.add(user); db.commit(); db.refresh(user)
    return {"message": "Account created", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}

@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": create_token(user), "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role}}

def case_dict(c: Case):
    return {"id": c.id, "case_code": c.case_code, "reporter_name": c.reporter_name, "reporter_contact": c.reporter_contact,
            "description": c.description, "category": c.category, "urgency": c.urgency, "ai_summary": c.ai_summary,
            "latitude": c.latitude, "longitude": c.longitude, "location_text": c.location_text, "status": c.status,
            "ngo_id": c.ngo_id, "ngo_name": c.ngo.name if c.ngo else None, "assigned_worker": c.assigned_worker,
            "created_at": c.created_at.isoformat() if c.created_at else None, "updated_at": c.updated_at.isoformat() if c.updated_at else None}

@app.post("/api/reports")
def create_report(data: ReportIn, db: Session = Depends(get_db), user: User | None = Depends(current_user)):
    category = classify_need(data.description)
    case = Case(case_code="SA-" + uuid4().hex[:8].upper(), reporter_name=data.reporter_name.strip() or "Anonymous",
                reporter_contact=data.reporter_contact.strip(), description=data.description.strip(), category=category,
                urgency=assess_urgency(data.description), ai_summary=summarize(data.description), latitude=data.latitude,
                longitude=data.longitude, location_text=data.location_text.strip(), status="pending_verification")
    db.add(case); db.commit(); db.refresh(case)
    existing = db.scalars(select(Case).where(Case.id != case.id).order_by(desc(Case.created_at)).limit(100)).all()
    return {"case": case_dict(case), "possible_duplicates": duplicate_candidates(case.description, existing),
            "notice": "AI suggestions are not a diagnosis or verification. A human must review the case."}

@app.get("/api/reports")
def list_reports(status_filter: str | None = None, category: str | None = None, db: Session = Depends(get_db)):
    query = select(Case).order_by(desc(Case.created_at))
    if status_filter:
        query = query.where(Case.status == status_filter)
    if category:
        query = query.where(Case.category == category)
    return [case_dict(c) for c in db.scalars(query.limit(500)).all()]

@app.get("/api/reports/{case_code}")
def get_report(case_code: str, db: Session = Depends(get_db)):
    case = db.scalar(select(Case).where(Case.case_code == case_code))
    if not case: raise HTTPException(404, "Case not found")
    return case_dict(case)

@app.get("/api/reports/{case_code}/matches")
def get_matches(case_code: str, db: Session = Depends(get_db)):
    case = db.scalar(select(Case).where(Case.case_code == case_code))
    if not case: raise HTTPException(404, "Case not found")
    ngos = db.scalars(select(NGO).where(NGO.verified.is_(True))).all()
    results = []
    for ngo in ngos:
        services = {x.strip().lower() for x in ngo.services.split(",")}
        if case.category not in services or ngo.active_cases >= ngo.capacity:
            continue
        distance_km = None
        if case.latitude is not None and case.longitude is not None:
            distance_km = round(haversine(case.latitude, case.longitude, ngo.latitude, ngo.longitude), 1)
        results.append({"id": ngo.id, "name": ngo.name, "services": ngo.services, "address": ngo.address,
                        "capacity": ngo.capacity, "active_cases": ngo.active_cases, "available_slots": ngo.capacity - ngo.active_cases,
                        "distance_km": distance_km, "contact": ngo.contact})
    results.sort(key=lambda x: (x["distance_km"] is None, x["distance_km"] if x["distance_km"] is not None else 99999))
    return results

def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    dlat, dlon = radians(lat2-lat1), radians(lon2-lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2*r*asin(sqrt(a))

@app.get("/api/ngos")
def list_ngos(db: Session = Depends(get_db)):
    return [{"id": n.id, "name": n.name, "services": n.services, "address": n.address, "latitude": n.latitude,
             "longitude": n.longitude, "capacity": n.capacity, "active_cases": n.active_cases,
             "verified": n.verified, "contact": n.contact} for n in db.scalars(select(NGO)).all()]

@app.post("/api/reports/{case_code}/verify")
def verify_case(case_code: str, data: VerifyIn, db: Session = Depends(get_db), user: User = Depends(require_roles("field_worker", "admin"))):
    case = db.scalar(select(Case).where(Case.case_code == case_code))
    if not case: raise HTTPException(404, "Case not found")
    case.status = "verified" if data.approved else "rejected"
    case.verified_by = user.id
    db.commit(); db.refresh(case)
    return case_dict(case)

@app.post("/api/reports/{case_code}/assign")
def assign_case(case_code: str, data: AssignIn, db: Session = Depends(get_db), user: User = Depends(require_roles("field_worker", "admin"))):
    case = db.scalar(select(Case).where(Case.case_code == case_code))
    ngo = db.get(NGO, data.ngo_id)
    if not case: raise HTTPException(404, "Case not found")
    if not ngo or not ngo.verified: raise HTTPException(400, "Choose a verified NGO")
    if case.category not in {s.strip().lower() for s in ngo.services.split(",")}: raise HTTPException(400, "NGO does not provide this service")
    if ngo.active_cases >= ngo.capacity: raise HTTPException(409, "NGO has no available capacity")
    if case.status not in ("verified", "assigned"): raise HTTPException(409, "Verify the case before assigning it")
    if case.ngo_id != ngo.id: ngo.active_cases += 1
    case.ngo_id = ngo.id; case.assigned_worker = data.assigned_worker.strip(); case.status = "assigned"
    db.commit(); db.refresh(case)
    return case_dict(case)

@app.post("/api/reports/{case_code}/status")
def update_status(case_code: str, data: StatusIn, db: Session = Depends(get_db), user: User = Depends(require_roles("field_worker", "ngo", "admin"))):
    case = db.scalar(select(Case).where(Case.case_code == case_code))
    if not case: raise HTTPException(404, "Case not found")
    allowed = {"assigned": {"in_progress", "resolved"}, "in_progress": {"resolved"}, "resolved": set(), "rejected": set()}
    if data.status not in allowed.get(case.status, set()):
        raise HTTPException(409, f"Cannot change status from {case.status} to {data.status}")
    case.status = data.status
    if data.status == "resolved" and case.ngo_id:
        ngo = db.get(NGO, case.ngo_id)
        if ngo: ngo.active_cases = max(0, ngo.active_cases - 1)
    db.commit(); db.refresh(case)
    return {"case": case_dict(case), "note": data.note, "updated_by": user.name}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    cases = db.scalars(select(Case)).all()
    return {"total": len(cases), "pending_verification": sum(c.status == "pending_verification" for c in cases),
            "verified": sum(c.status == "verified" for c in cases), "assigned": sum(c.status == "assigned" for c in cases),
            "in_progress": sum(c.status == "in_progress" for c in cases), "resolved": sum(c.status == "resolved" for c in cases),
            "urgent_review": sum(c.urgency == "urgent_review" and c.status not in ("resolved", "rejected") for c in cases),
            "by_category": {k: sum(c.category == k for c in cases) for k in ["food", "shelter", "medical", "other"]}}
