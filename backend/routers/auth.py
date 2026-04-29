from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
import bcrypt
from jose import jwt

from database import get_db
from models.models import User, Company
from dependencies import SECRET_KEY, ALGORITHM, log_audit, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

def verify_password(plain_password, hashed_password):
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)

def get_password_hash(password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=1440))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login with:
      - SuperAdmin:     username = "superadmin"
      - Company users:  username = "localname@domain"  (e.g. "admin@lacesta")
    """
    raw_username = form_data.username.strip()

    if "@" in raw_username:
        local_part, domain = raw_username.rsplit("@", 1)
        company = db.query(Company).filter(
            Company.domain == domain.lower(),
            Company.is_active == True
        ).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Company domain not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = db.query(User).filter(
            User.username == local_part,
            User.company_id == company.id
        ).first()
    else:
        # SuperAdmin login — no @ required
        user = db.query(User).filter(
            User.username == raw_username,
            User.role == 'SuperAdmin'
        ).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.restaurant and not user.restaurant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your restaurant has been disabled. Please contact the administrator."
        )

    token_data = {
        "sub": str(user.id),
        "role": user.role,
        "company_id": user.company_id,
        "restaurant_id": user.restaurant_id,
        "production_plant_id": user.production_plant_id,
    }
    access_token = create_access_token(data=token_data)
    log_audit(db, user.id, "User Login", "User", user.id, "Successful login")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "company_id": user.company_id,
    }

@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "company_id": current_user.company_id,
        "restaurant_id": current_user.restaurant_id,
        "production_plant_id": current_user.production_plant_id,
    }

@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    log_audit(db, current_user.id, "Change Password", "User", current_user.id, "User changed their own password")
    return {"message": "Password changed successfully"}
