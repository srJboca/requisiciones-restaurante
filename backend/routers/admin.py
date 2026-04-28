from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.models import User, Restaurant, ProductGroup, Product, AuditLog, SystemSetting
from dependencies import get_current_admin, log_audit
from routers.auth import get_password_hash
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])

class RestaurantCreate(BaseModel):
    name: str
    location: str | None = None

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    restaurant_id: int | None = None

class ProductGroupCreate(BaseModel):
    name: str

class ProductCreate(BaseModel):
    name: str
    sku: str
    unit_measure: str
    group_id: int | None = None

class SettingUpdate(BaseModel):
    eta_days: str

class AdminPasswordReset(BaseModel):
    new_password: str

@router.post("/restaurants")
def create_restaurant(rest: RestaurantCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    new_rest = Restaurant(name=rest.name, location=rest.location)
    db.add(new_rest)
    db.commit()
    db.refresh(new_rest)
    log_audit(db, current_user.id, "Create Restaurant", "Restaurant", new_rest.id, f"Created {rest.name}")
    return new_rest

@router.post("/restaurants/{restaurant_id}/toggle")
def toggle_restaurant(restaurant_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    rest = db.query(Restaurant).filter(Restaurant.id == restaurant_id).first()
    if not rest:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    rest.is_active = not rest.is_active
    db.commit()
    action_str = "Enabled" if rest.is_active else "Disabled"
    log_audit(db, current_user.id, f"{action_str} Restaurant", "Restaurant", rest.id, f"{action_str} {rest.name}")
    return {"id": rest.id, "is_active": rest.is_active}

@router.post("/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, payload: AdminPasswordReset, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    log_audit(db, current_user.id, "Force Password Reset", "User", user.id, f"Admin forced password reset for {user.username}")
    
    return {"message": "Password reset successfully"}

@router.get("/restaurants")
def get_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).all()

@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    from routers.auth import get_password_hash
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(username=user.username, password_hash=hashed_password, role=user.role, restaurant_id=user.restaurant_id)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_audit(db, current_user.id, "Create User", "User", new_user.id, f"Created {user.username}")
    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@router.post("/product-groups")
def create_product_group(group: ProductGroupCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    new_group = ProductGroup(name=group.name)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    log_audit(db, current_user.id, "Create Product Group", "ProductGroup", new_group.id, f"Created {group.name}")
    return new_group

@router.get("/product-groups")
def get_product_groups(db: Session = Depends(get_db)):
    return db.query(ProductGroup).all()

@router.post("/products")
def create_product(product: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    if db.query(Product).filter(Product.sku == product.sku).first():
        raise HTTPException(status_code=400, detail="SKU already exists")
    new_product = Product(name=product.name, sku=product.sku, unit_measure=product.unit_measure, group_id=product.group_id)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    log_audit(db, current_user.id, "Create Product", "Product", new_product.id, f"Created {product.name} ({product.sku})")
    return new_product

@router.post("/products/{product_id}/toggle")
def toggle_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    prod = db.query(Product).filter(Product.id == product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    prod.is_active = not prod.is_active
    db.commit()
    action_str = "Enabled" if prod.is_active else "Disabled"
    log_audit(db, current_user.id, f"{action_str} Product", "Product", prod.id, f"{action_str} {prod.name} ({prod.sku})")
    return {"id": prod.id, "is_active": prod.is_active}

@router.get("/products")
def get_products(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(Product)
    if active_only:
        query = query.filter(Product.is_active == True)
    return query.all()

@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).all()

@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).filter(SystemSetting.setting_key == 'eta_days').first()
    return {"eta_days": setting.setting_value if setting else "2"}

@router.post("/settings")
def update_settings(data: SettingUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    setting = db.query(SystemSetting).filter(SystemSetting.setting_key == 'eta_days').first()
    if not setting:
        setting = SystemSetting(setting_key='eta_days', setting_value=data.eta_days)
        db.add(setting)
    else:
        setting.setting_value = data.eta_days
    db.commit()
    log_audit(db, current_user.id, "Update Settings", "SystemSetting", None, f"Updated eta_days to {data.eta_days}")
    return {"message": "Settings updated"}
