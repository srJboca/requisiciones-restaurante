from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from database import get_db
from models.models import User
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "supersecretkey_change_in_production")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user

# ── Role guards ────────────────────────────────────────────────

def get_current_superadmin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != 'SuperAdmin':
        raise HTTPException(status_code=403, detail="SuperAdmin access required")
    return current_user

def get_current_company_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != 'CompanyAdmin':
        raise HTTPException(status_code=403, detail="CompanyAdmin access required")
    return current_user

def get_current_restaurant(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != 'Restaurant':
        raise HTTPException(status_code=403, detail="Restaurant access required")
    return current_user

def get_current_production(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != 'Production Plant':
        raise HTTPException(status_code=403, detail="Production Plant access required")
    return current_user

def get_current_business_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != 'Business User':
        raise HTTPException(status_code=403, detail="Business User access required")
    return current_user

# SuperAdmin OR CompanyAdmin (used for shared endpoints)
def get_current_admin_any(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ('SuperAdmin', 'CompanyAdmin'):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# Anyone who can see dashboards (Admin OR Business User)
def get_analytical_access(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ('SuperAdmin', 'CompanyAdmin', 'Business User'):
        raise HTTPException(status_code=403, detail="Analytical access required")
    return current_user

# ── Audit helper ───────────────────────────────────────────────

def log_audit(db: Session, user_id: int, action: str, entity_type: str, entity_id: int = None, details: str = None):
    from models.models import AuditLog
    audit = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details
    )
    db.add(audit)
    db.commit()
