"""
SuperAdmin router — platform-level management.
All routes require SuperAdmin role.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database import get_db
from models.models import Company, User, Restaurant, Order, SystemSetting
from dependencies import get_current_superadmin, log_audit
from routers.auth import get_password_hash

router = APIRouter(prefix="/superadmin", tags=["superadmin"])

# ── Schemas ─────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    name: str
    domain: str

class AdminCreate(BaseModel):
    username: str
    password: str

class SettingUpdate(BaseModel):
    eta_days: Optional[int] = None
    default_language: Optional[str] = None

# ── Company CRUD ─────────────────────────────────────────────

@router.get("/companies")
def list_companies(db: Session = Depends(get_db), _=Depends(get_current_superadmin)):
    companies = db.query(Company).all()
    result = []
    for c in companies:
        result.append({
            "id": c.id,
            "name": c.name,
            "domain": c.domain,
            "is_active": c.is_active,
            "restaurant_count": len(c.restaurants),
            "user_count": len(c.users),
        })
    return result

@router.post("/companies")
def create_company(payload: CompanyCreate, db: Session = Depends(get_db), current_user=Depends(get_current_superadmin)):
    domain = payload.domain.lower().strip()
    if db.query(Company).filter(Company.domain == domain).first():
        raise HTTPException(status_code=400, detail="Domain already exists")
    company = Company(name=payload.name, domain=domain)
    db.add(company)
    db.commit()
    db.refresh(company)
    log_audit(db, current_user.id, "Create Company", "Company", company.id, f"Created company {company.name}")
    return {"id": company.id, "name": company.name, "domain": company.domain}

@router.post("/companies/{company_id}/toggle")
def toggle_company(company_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_superadmin)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.is_active = not company.is_active
    db.commit()
    log_audit(db, current_user.id, "Toggle Company", "Company", company.id, f"Set active={company.is_active}")
    return {"id": company.id, "is_active": company.is_active}

# ── Company Admin management ─────────────────────────────────

@router.post("/companies/{company_id}/admin")
def create_company_admin(
    company_id: int,
    payload: AdminCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_superadmin)
):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    existing = db.query(User).filter(User.username == payload.username, User.company_id == company_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists in this company")
    admin = User(
        username=payload.username,
        password_hash=get_password_hash(payload.password),
        role='CompanyAdmin',
        company_id=company_id,
    )
    db.add(admin)
    db.commit()
    log_audit(db, current_user.id, "Create CompanyAdmin", "User", admin.id, f"Created admin for company {company_id}")
    return {"id": admin.id, "username": admin.username, "company": company.domain}

# ── Global Settings ──────────────────────────────────────────

@router.get("/settings")
def get_global_settings(db: Session = Depends(get_db), _=Depends(get_current_superadmin)):
    rows = db.query(SystemSetting).filter(SystemSetting.company_id == None).all()
    return {r.setting_key: r.setting_value for r in rows}

@router.post("/settings")
def update_global_settings(payload: SettingUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_superadmin)):
    def _set(key, value):
        row = db.query(SystemSetting).filter(SystemSetting.company_id == None, SystemSetting.setting_key == key).first()
        if row:
            row.setting_value = str(value)
        else:
            db.add(SystemSetting(company_id=None, setting_key=key, setting_value=str(value)))
    if payload.eta_days is not None:
        _set('eta_days', payload.eta_days)
    if payload.default_language is not None:
        _set('default_language', payload.default_language)
    db.commit()
    log_audit(db, current_user.id, "Update Global Settings", "SystemSetting")
    return {"message": "Global settings updated"}

# ── Cross-company reporting ──────────────────────────────────

@router.get("/history")
def get_all_history(db: Session = Depends(get_db), _=Depends(get_current_superadmin)):
    orders = db.query(Order).order_by(Order.order_date.desc()).all()
    result = []
    for o in orders:
        result.append({
            "order_id": o.id,
            "company_name": o.restaurant.company.name if o.restaurant and o.restaurant.company else "Unknown",
            "restaurant_name": o.restaurant.name if o.restaurant else "Unknown",
            "order_date": o.order_date,
            "status": o.status,
            "submitted_by_name": o.submitted_by.username if o.submitted_by else None,
            "shipped_by_name": o.shipped_by.username if o.shipped_by else None,
            "received_by_name": o.received_by.username if o.received_by else None,
            "items": [{
                "product_name": i.product.name,
                "sku": i.product.sku,
                "required_quantity": float(i.required_quantity),
                "shipped_quantity": float(i.shipped_quantity) if i.shipped_quantity else 0,
                "received_quantity": float(i.received_quantity) if i.received_quantity else 0,
            } for i in o.items]
        })
    return result

@router.get("/audit-logs")
def get_all_audit_logs(db: Session = Depends(get_db), _=Depends(get_current_superadmin)):
    from models.models import AuditLog
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(500).all()
    return [{
        "id": l.id,
        "user": l.user.username if l.user else "system",
        "action": l.action,
        "entity_type": l.entity_type,
        "entity_id": l.entity_id,
        "details": l.details,
        "timestamp": str(l.timestamp),
    } for l in logs]
