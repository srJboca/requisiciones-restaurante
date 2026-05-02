"""
CompanyAdmin router — all operations scoped to the current user's company.
"""
import csv
import io
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from database import get_db
from models.models import User, Restaurant, ProductGroup, Product, AuditLog, SystemSetting, Order, ProductionPlant
from dependencies import get_current_company_admin, log_audit
from routers.auth import get_password_hash

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ── Schemas ──────────────────────────────────────────────────

class RestaurantCreate(BaseModel):
    name: str
    location: Optional[str] = None
    production_plant_id: Optional[int] = None

class RestaurantUpdate(BaseModel):
    production_plant_id: Optional[int] = None

class POSMappingBulkUpdate(BaseModel):
    product_name: str
    alternative_name: Optional[str] = None
    category_name: Optional[str] = "Uncategorized"
    is_ignored: bool = False

class ProductionPlantCreate(BaseModel):
    name: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str
    subrole: Optional[str] = "Requisition"
    restaurant_id: Optional[int] = None
    production_plant_id: Optional[int] = None

class NPSQuestionCreate(BaseModel):
    question_text: str
    question_type: str = "score" # score, text, yes_no
    is_active: bool = True
    display_order: int = 0

class ProductGroupCreate(BaseModel):
    name: str

class ProductCreate(BaseModel):
    name: str
    sku: str
    unit_measure: str
    group_id: Optional[int] = None

class SettingUpdate(BaseModel):
    eta_days: Optional[str] = None
    default_language: Optional[str] = None

class AdminPasswordReset(BaseModel):
    new_password: str

# ── Helper ───────────────────────────────────────────────────

def _get_setting(db, company_id, key):
    """Get company-specific setting, falling back to global default."""
    row = db.query(SystemSetting).filter(
        SystemSetting.company_id == company_id,
        SystemSetting.setting_key == key
    ).first()
    if not row:
        row = db.query(SystemSetting).filter(
            SystemSetting.company_id == None,
            SystemSetting.setting_key == key
        ).first()
    return row.setting_value if row else None

def _set_setting(db, company_id, key, value):
    row = db.query(SystemSetting).filter(
        SystemSetting.company_id == company_id,
        SystemSetting.setting_key == key
    ).first()
    if row:
        row.setting_value = str(value)
    else:
        db.add(SystemSetting(company_id=company_id, setting_key=key, setting_value=str(value)))

# ── Production Plants ────────────────────────────────────────

@router.get("/production-plants")
def get_production_plants(db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    plants = db.query(ProductionPlant).filter(ProductionPlant.company_id == current_user.company_id).all()
    return [{"id": p.id, "name": p.name, "is_active": p.is_active,
             "restaurant_count": len(p.restaurants)} for p in plants]

@router.post("/production-plants")
def create_production_plant(payload: ProductionPlantCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    plant = ProductionPlant(name=payload.name, company_id=current_user.company_id)
    db.add(plant)
    db.commit()
    db.refresh(plant)
    log_audit(db, current_user.id, "Create Production Plant", "ProductionPlant", plant.id, f"Created {plant.name}")
    return {"id": plant.id, "name": plant.name}

@router.post("/production-plants/{plant_id}/toggle")
def toggle_production_plant(plant_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    plant = db.query(ProductionPlant).filter(ProductionPlant.id == plant_id, ProductionPlant.company_id == current_user.company_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="Production plant not found")
    plant.is_active = not plant.is_active
    db.commit()
    return {"id": plant.id, "is_active": plant.is_active}

# ── Restaurants ──────────────────────────────────────────────

@router.get("/restaurants")
def get_restaurants(db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    rests = db.query(Restaurant).filter(Restaurant.company_id == current_user.company_id).all()
    return [{"id": r.id, "name": r.name, "location": r.location, "is_active": r.is_active,
             "production_plant_id": r.production_plant_id,
             "production_plant_name": r.production_plant.name if r.production_plant else None} for r in rests]

@router.post("/restaurants")
def create_restaurant(rest: RestaurantCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    if rest.production_plant_id:
        plant = db.query(ProductionPlant).filter(
            ProductionPlant.id == rest.production_plant_id,
            ProductionPlant.company_id == current_user.company_id
        ).first()
        if not plant:
            raise HTTPException(status_code=400, detail="Production plant not found in your company")
    new_rest = Restaurant(name=rest.name, location=rest.location,
                          company_id=current_user.company_id,
                          production_plant_id=rest.production_plant_id)
    db.add(new_rest)
    db.commit()
    db.refresh(new_rest)
    log_audit(db, current_user.id, "Create Restaurant", "Restaurant", new_rest.id, f"Created {rest.name}")
    return {"id": new_rest.id, "name": new_rest.name}

@router.post("/restaurants/{restaurant_id}/toggle")
def toggle_restaurant(restaurant_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    rest = db.query(Restaurant).filter(Restaurant.id == restaurant_id, Restaurant.company_id == current_user.company_id).first()
    if not rest:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    rest.is_active = not rest.is_active
    db.commit()
    log_audit(db, current_user.id, "Toggle Restaurant", "Restaurant", rest.id, f"Set active={rest.is_active}")
    return {"id": rest.id, "is_active": rest.is_active}

@router.put("/restaurants/{restaurant_id}")
def update_restaurant(restaurant_id: int, payload: RestaurantUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    rest = db.query(Restaurant).filter(Restaurant.id == restaurant_id, Restaurant.company_id == current_user.company_id).first()
    if not rest:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if payload.production_plant_id is not None:
        plant = db.query(ProductionPlant).filter(
            ProductionPlant.id == payload.production_plant_id,
            ProductionPlant.company_id == current_user.company_id
        ).first()
        if not plant:
            raise HTTPException(status_code=400, detail="Production plant not found in your company")
        rest.production_plant_id = payload.production_plant_id
    db.commit()
    return {"id": rest.id, "production_plant_id": rest.production_plant_id}

# ── Users ────────────────────────────────────────────────────

@router.get("/users")
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    users = db.query(User).filter(User.company_id == current_user.company_id).all()
    return [{"id": u.id, "username": u.username, "role": u.role, "subrole": u.subrole,
             "restaurant_id": u.restaurant_id, "production_plant_id": u.production_plant_id} for u in users]

@router.post("/users")
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    if user.role not in ('CompanyAdmin', 'Restaurant', 'Production Plant'):
        raise HTTPException(status_code=400, detail="Invalid role for company user")
    if db.query(User).filter(User.username == user.username, User.company_id == current_user.company_id).first():
        raise HTTPException(status_code=400, detail="Username already exists in this company")

    prod_plant_id = None
    if user.role == 'Production Plant':
        if not user.production_plant_id:
            raise HTTPException(status_code=400, detail="Production plant must be assigned for Production Plant users")
        plant = db.query(ProductionPlant).filter(
            ProductionPlant.id == user.production_plant_id,
            ProductionPlant.company_id == current_user.company_id
        ).first()
        if not plant:
            raise HTTPException(status_code=400, detail="Production plant not found in your company")
        prod_plant_id = user.production_plant_id

    rest_id = None
    if user.role == 'Restaurant':
        if not user.restaurant_id:
            raise HTTPException(status_code=400, detail="Restaurant must be assigned for Restaurant users")
        rest = db.query(Restaurant).filter(
            Restaurant.id == user.restaurant_id,
            Restaurant.company_id == current_user.company_id
        ).first()
        if not rest:
            raise HTTPException(status_code=400, detail="Restaurant not found in your company")
        rest_id = user.restaurant_id

    new_user = User(
        username=user.username,
        password_hash=get_password_hash(user.password),
        role=user.role,
        subrole=user.subrole,
        company_id=current_user.company_id,
        restaurant_id=rest_id,
        production_plant_id=prod_plant_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    log_audit(db, current_user.id, "Create User", "User", new_user.id, f"Created {user.username} ({user.role})")
    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}

@router.post("/users/{user_id}/reset-password")
def admin_reset_password(user_id: int, payload: AdminPasswordReset, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    user = db.query(User).filter(User.id == user_id, User.company_id == current_user.company_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    log_audit(db, current_user.id, "Force Password Reset", "User", user.id, f"Admin reset password for {user.username}")
    return {"message": "Password reset successfully"}

# ── Product Groups ───────────────────────────────────────────

@router.get("/product-groups")
def get_product_groups(db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    return db.query(ProductGroup).filter(ProductGroup.company_id == current_user.company_id).all()

@router.post("/product-groups")
def create_product_group(group: ProductGroupCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    new_group = ProductGroup(name=group.name, company_id=current_user.company_id)
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    log_audit(db, current_user.id, "Create Product Group", "ProductGroup", new_group.id, f"Created {group.name}")
    return new_group

# ── Products ─────────────────────────────────────────────────

@router.get("/products")
def get_products(active_only: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    query = db.query(Product).filter(Product.company_id == current_user.company_id)
    if active_only:
        query = query.filter(Product.is_active == True)
    return query.all()

@router.post("/products")
def create_product(product: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    if db.query(Product).filter(Product.sku == product.sku, Product.company_id == current_user.company_id).first():
        raise HTTPException(status_code=400, detail="SKU already exists in your company")
    new_product = Product(name=product.name, sku=product.sku, unit_measure=product.unit_measure,
                          group_id=product.group_id, company_id=current_user.company_id)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    log_audit(db, current_user.id, "Create Product", "Product", new_product.id, f"Created {product.name} ({product.sku})")
    return new_product

@router.post("/products/{product_id}/toggle")
def toggle_product(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    prod = db.query(Product).filter(Product.id == product_id, Product.company_id == current_user.company_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    prod.is_active = not prod.is_active
    db.commit()
    return {"id": prod.id, "is_active": prod.is_active}

@router.get("/products/template")
def download_product_template(_: User = Depends(get_current_company_admin)):
    """Download a CSV template for bulk product import."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "sku", "unit_measure", "group_name"])
    writer.writerow(["Arroz 500g", "ARR-001", "Kg", "Abarrotes"])
    writer.writerow(["Leche Entera", "LEC-001", "Litro", "Lacteos"])
    writer.writerow(["Pan Tajado", "PAN-001", "Unidad", "Panaderia"])
    # BOM (utf-8-sig) ensures Excel opens it correctly
    content = "\ufeff" + output.getvalue()
    return StreamingResponse(
        io.BytesIO(content.encode("utf-8")),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="product_template.csv"'},
    )

@router.post("/products/import")
def import_products(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_company_admin),
):
    """Bulk-import products from a CSV file.

    Expected columns: name, sku, unit_measure, group_name
    - Rows with missing required fields are skipped.
    - Duplicate SKUs (within the company) are skipped.
    - group_name is created automatically if it doesn't exist.
    """
    # Read and decode — handle both utf-8 and utf-8-sig (Excel BOM)
    try:
        raw = file.file.read()
        content = raw.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read file. Ensure it is a valid UTF-8 CSV.")

    reader = csv.DictReader(io.StringIO(content))

    # Validate headers
    required_headers = {"name", "sku", "unit_measure"}
    if reader.fieldnames is None or not required_headers.issubset(set(reader.fieldnames)):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain columns: name, sku, unit_measure (and optionally group_name). Found: {reader.fieldnames}"
        )

    imported, skipped, updated = 0, 0, 0
    errors: list[str] = []
    group_cache: dict[str, int] = {}  # group_name → group_id to avoid repeated lookups
    
    # Pre-load existing products to avoid duplicate queries and handle duplicates within the CSV itself
    existing_products = db.query(Product).filter(Product.company_id == current_user.company_id).all()
    sku_cache = {p.sku: p for p in existing_products}

    for row_num, row in enumerate(reader, start=2):  # 2 = first data row
        name = (row.get("name") or "").strip()
        sku = (row.get("sku") or "").strip()
        unit_measure = (row.get("unit_measure") or "").strip()
        group_name = (row.get("group_name") or "").strip()

        # Required field check
        if not name or not sku or not unit_measure:
            errors.append(f"Row {row_num}: missing required field(s) — skipped.")
            skipped += 1
            continue

        # Resolve product group
        group_id = None
        if group_name:
            if group_name in group_cache:
                group_id = group_cache[group_name]
            else:
                group = db.query(ProductGroup).filter(
                    ProductGroup.name == group_name,
                    ProductGroup.company_id == current_user.company_id
                ).first()
                if not group:
                    group = ProductGroup(name=group_name, company_id=current_user.company_id)
                    db.add(group)
                    db.flush()  # get the auto-generated id
                group_cache[group_name] = group.id
                group_id = group.id

        if sku in sku_cache:
            # Update existing product
            prod = sku_cache[sku]
            prod.name = name
            prod.unit_measure = unit_measure
            prod.group_id = group_id
            updated += 1
        else:
            # Create new product
            new_prod = Product(
                name=name, sku=sku, unit_measure=unit_measure,
                group_id=group_id, company_id=current_user.company_id
            )
            db.add(new_prod)
            sku_cache[sku] = new_prod
            imported += 1

    db.commit()
    log_audit(
        db, current_user.id, "Import Products CSV", "Product",
        details=f"Imported {imported}, updated {updated}, skipped {skipped}"
    )
    return {
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "errors": errors,
        "message": f"Imported {imported} new product(s). Updated {updated} existing. {skipped} row(s) skipped."
    }

# ── Settings ─────────────────────────────────────────────────

@router.get("/settings")
def get_settings(db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    return {
        "eta_days": _get_setting(db, current_user.company_id, 'eta_days') or "2",
        "default_language": _get_setting(db, current_user.company_id, 'default_language') or "en",
    }

@router.post("/settings")
def update_settings(data: SettingUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    if data.eta_days is not None:
        _set_setting(db, current_user.company_id, 'eta_days', data.eta_days)
    if data.default_language is not None:
        _set_setting(db, current_user.company_id, 'default_language', data.default_language)
    db.commit()
    log_audit(db, current_user.id, "Update Settings", "SystemSetting")
    return {"message": "Settings updated"}

# ── Audit Logs ───────────────────────────────────────────────

@router.get("/audit-logs")
def get_audit_logs(db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    # Show logs from users of this company only
    company_user_ids = [u.id for u in db.query(User).filter(User.company_id == current_user.company_id).all()]
    logs = db.query(AuditLog).filter(AuditLog.user_id.in_(company_user_ids)).order_by(AuditLog.timestamp.desc()).limit(200).all()
    return [{"id": l.id, "user": l.user.username if l.user else "system",
             "action": l.action, "entity_type": l.entity_type, "entity_id": l.entity_id,
             "details": l.details, "timestamp": str(l.timestamp)} for l in logs]

# ── History ──────────────────────────────────────────────────

@router.get("/history")
def get_history(order_date: str | None = None, restaurant_id: int | None = None,
                db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    company_rest_ids = [r.id for r in db.query(Restaurant).filter(Restaurant.company_id == current_user.company_id).all()]
    query = db.query(Order).filter(Order.restaurant_id.in_(company_rest_ids)).order_by(Order.order_date.desc())
    if order_date:
        query = query.filter(Order.order_date == order_date)
    if restaurant_id and restaurant_id in company_rest_ids:
        query = query.filter(Order.restaurant_id == restaurant_id)

    orders = query.all()
    result = []
    for o in orders:
        result.append({
            "order_id": o.id,
            "restaurant_name": o.restaurant.name if o.restaurant else "Unknown",
            "order_date": o.order_date,
            "status": o.status,
            "submitted_by_name": o.submitted_by.username if o.submitted_by else None,
            "shipped_by_name": o.shipped_by.username if o.shipped_by else None,
            "received_by_name": o.received_by.username if o.received_by else None,
            "items": [{
                "item_id": i.id, "product_name": i.product.name, "sku": i.product.sku,
                "required_quantity": float(i.required_quantity),
                "shipped_quantity": float(i.shipped_quantity) if i.shipped_quantity else 0,
                "received_quantity": float(i.received_quantity) if i.received_quantity else 0,
            } for i in o.items]
        })
    return result

# ── Sales & Analytics Helpers ───────────────────────────────

def parse_colombian_float(val) -> float:
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).strip()
        # If it has both . and , it's definitely 1.234,56 or 1,234.56
        # If it only has one, it could be decimal or thousands.
        # Sample CSV 8000 is easy. 8.000 could be 8 or 8000.
        # Standard cleaning: remove common thousands separators if it looks like Colombian format
        if "," in s and "." in s:
            if s.find(".") < s.find(","): # 1.234,56
                s = s.replace(".", "").replace(",", ".")
            else: # 1,234.56
                s = s.replace(",", "")
        elif "," in s: # Assume it's decimal separator 8,5
            s = s.replace(",", ".")
        return float(s)
    except Exception:
        return 0.0

# ── Sales & Analytics ────────────────────────────────────────

@router.post("/sales/upload")
async def upload_sales(
    restaurant_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_company_admin),
):
    logger.info(f"Uploading sales for restaurant {restaurant_id} by user {current_user.username}")
    rest = db.query(Restaurant).filter(Restaurant.id == restaurant_id, Restaurant.company_id == current_user.company_id).first()
    if not rest:
        logger.error(f"Restaurant {restaurant_id} not found or doesn't belong to company {current_user.company_id}")
        raise HTTPException(status_code=404, detail="Restaurant not found")

    try:
        raw = await file.read()
        content = raw.decode("utf-8-sig")
        logger.info(f"File read successfully, size: {len(raw)} bytes")
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=400, detail="Could not read file. Ensure valid CSV.")

    sniffer = csv.Sniffer()
    try:
        # Try to detect the dialect
        dialect = sniffer.sniff(content[:4096], delimiters=',;|')
        reader = csv.DictReader(io.StringIO(content), dialect=dialect)
        logger.info(f"Detected CSV dialect: '{dialect.delimiter}'")
    except Exception as e:
        logger.warning(f"Sniffer failed, trying manual detection: {e}")
        # Manual fallback for common delimiters
        first_line = content.split('\n')[0]
        if '|' in first_line:
            reader = csv.DictReader(io.StringIO(content), delimiter='|')
        elif ';' in first_line:
            reader = csv.DictReader(io.StringIO(content), delimiter=';')
        else:
            reader = csv.DictReader(io.StringIO(content))

    from models.models import POSSale
    imported = 0
    
    # We'll store records in a list first to identify which orders to clear
    new_records = []
    order_refs_to_clear = set()
    
    for row in reader:
        # Normalize keys (strip whitespace, upper case for matching)
        norm_row = { (k.strip().upper() if k else ""): (v.strip() if v else "") for k, v in row.items() }
        
        # Match columns case-insensitively
        product_name = norm_row.get("PRODUCTO", "").title()
        
        # Skip separators or empty product names
        if "===" in product_name or not product_name:
            continue
            
        order_ref = norm_row.get("ORDEN", "")
        if order_ref:
            order_refs_to_clear.add(order_ref)

        pos_sale = POSSale(
            restaurant_id=restaurant_id,
            company_id=current_user.company_id,
            order_ref=order_ref,
            date_open=norm_row.get("FECHA_APERTURA", ""),
            date_close=norm_row.get("FECHA_CIERRE", ""),
            payment_method=norm_row.get("MEDIODEPAGO", ""),
            product_name=product_name,
            quantity=parse_colombian_float(norm_row.get("CANTIDAD", 0)),
            diners=int(parse_colombian_float(norm_row.get("COMENSALES", 0))),
            price_with_tax=parse_colombian_float(norm_row.get("PRECIOCONIMPUESTO", 0)),
            total_tip=parse_colombian_float(norm_row.get("TOTALPROPINA", 0)),
        )
        new_records.append(pos_sale)
        imported += 1
        
    # Atomic replace: Clear existing orders found in this batch for this specific restaurant
    if order_refs_to_clear:
        # Convert set to list for SQLAlchemy IN clause
        # We limit the batch size if needed, but for a single CSV it should be fine
        db.query(POSSale).filter(
            POSSale.restaurant_id == restaurant_id,
            POSSale.order_ref.in_(list(order_refs_to_clear))
        ).delete(synchronize_session=False)

    # Insert new records
    for record in new_records:
        db.add(record)
        
    db.commit()
    logger.info(f"Imported {imported} records for restaurant {restaurant_id} (replaced existing orders if any)")
    log_audit(db, current_user.id, "Upload Sales CSV", "POSSale", details=f"Imported {imported} sales records for restaurant {restaurant_id}. Replaced overlapping order references.")
    return {"message": f"Successfully imported {imported} sales records."}

@router.get("/sales/abc-report")
def get_abc_report(view_type: str = "product", db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    from models.models import POSSale, POSProductMapping
    import pandas as pd
    
    # Get all mappings
    mappings = db.query(POSProductMapping).filter(POSProductMapping.company_id == current_user.company_id).all()
    mapping_dict = {m.product_name: {"category": m.category_name, "ignored": m.is_ignored, "alt_name": m.alternative_name} for m in mappings}
    
    sales = db.query(POSSale).filter(POSSale.company_id == current_user.company_id).all()
    if not sales:
        return {}

    data = []
    for s in sales:
        # Resolve mapping
        m = mapping_dict.get(s.product_name, {"category": "Uncategorized", "ignored": False, "alt_name": None})
        
        # Skip ignored products
        if m["ignored"]:
            continue
            
        # Use alternative name if defined, otherwise original POS name
        display_name = m["alt_name"] if m.get("alt_name") else s.product_name
            
        data.append({
            "SUCURSAL": str(s.restaurant_id),
            "ORDEN": s.order_ref,
            "PRODUCTO": display_name,
            "CATEGORIA": m["category"],
            "CANTIDAD": float(s.quantity),
            "COMENSALES": s.diners,
            "Venta_Total_Linea": float(s.price_with_tax) if s.price_with_tax else 0
        })
        
    df = pd.DataFrame(data)
    if df.empty:
        return {}
        
    # Determine the grouping key for analysis
    group_key = "CATEGORIA" if view_type == "category" else "PRODUCTO"
        
    def analizar_sucursal(df_filtrado):
        # 1. KPIs
        ordenes = df_filtrado.groupby('ORDEN').agg({
            'Venta_Total_Linea': 'sum',
            'COMENSALES': 'max'
        })
        total_ordenes = len(ordenes)
        ticket_promedio = ordenes['Venta_Total_Linea'].mean() if total_ordenes > 0 else 0
        comensales_promedio = ordenes['COMENSALES'].mean() if total_ordenes > 0 else 0
        
        kpi = {
            "orders": f"{total_ordenes:,.0f}",
            "ticket": f"${ticket_promedio:,.0f}",
            "diners": f"{comensales_promedio:.1f}"
        }
        
        # 2. PARETO
        ventas_prod = df_filtrado.groupby(group_key)['Venta_Total_Linea'].sum().sort_values(ascending=False)
        top_pareto = ventas_prod.head(10)
        pareto = {
            "labels": top_pareto.index.tolist(),
            "data": top_pareto.values.tolist()
        }
        
        # 3. ANCLAS
        cantidades_prod = df_filtrado.groupby(group_key)['CANTIDAD'].sum().sort_values(ascending=False)
        top_anclas = cantidades_prod.head(3)
        anclas = []
        iconos = ['fa-star', 'fa-fire', 'fa-bolt']
        for i, (prod, cant) in enumerate(top_anclas.items()):
            anclas.append({
                "name": prod,
                "icon": iconos[i] if i < len(iconos) else 'fa-star',
                "qty": f"{cant:,.0f} und",
                "mix": "Alta tracción"
            })
            
        # 4. PORTAFOLIO (Revenue-based ABC)
        total_revenue = ventas_prod.sum()
        cumulative_revenue = ventas_prod.cumsum() / total_revenue if total_revenue > 0 else ventas_prod
        
        full_portfolio = []
        cat_A = []
        cat_B = []
        cat_C = []
        
        for name, cum_pct in cumulative_revenue.items():
            rev = float(ventas_prod[name])
            qty = float(df_filtrado[df_filtrado[group_key] == name]['CANTIDAD'].sum())
            
            # Standard ABC 80/15/5 rule
            if cum_pct <= 0.80:
                abc_class = 'A'
                if len(cat_A) < 5: cat_A.append(name)
            elif cum_pct <= 0.95:
                abc_class = 'B'
                if len(cat_B) < 5: cat_B.append(name)
            else:
                abc_class = 'C'
                if len(cat_C) < 5: cat_C.append({"name": name, "reason": "Baja rotación."})
            
            full_portfolio.append({
                "name": name,
                "revenue": rev,
                "quantity": qty,
                "share": float(rev / total_revenue) if total_revenue > 0 else 0,
                "cumulative": float(cum_pct),
                "abc": abc_class
            })
            
        portafolio = {
            "catA": cat_A,
            "catB": cat_B,
            "catC": cat_C,
            "full": full_portfolio,
            "quantity_full": [] # Will populate below
        }
        
        # 4b. QUANTITY PORTAFOLIO (Quantity-based ABC)
        total_qty = cantidades_prod.sum()
        cumulative_qty = cantidades_prod.cumsum() / total_qty if total_qty > 0 else cantidades_prod
        for name, cum_pct in cumulative_qty.items():
            qty = float(cantidades_prod[name])
            rev = float(df_filtrado[df_filtrado[group_key] == name]['Venta_Total_Linea'].sum())
            
            if cum_pct <= 0.80: abc_class = 'A'
            elif cum_pct <= 0.95: abc_class = 'B'
            else: abc_class = 'C'
            
            portafolio["quantity_full"].append({
                "name": name,
                "revenue": rev,
                "quantity": qty,
                "share": float(qty / total_qty) if total_qty > 0 else 0,
                "cumulative": float(cum_pct),
                "abc": abc_class
            })
            
        # 5. CORRELACION (Only makes sense for products usually, but we keep it generic)
        from collections import Counter
        from itertools import combinations
        
        ordenes_con_prods = df_filtrado.groupby('ORDEN')[group_key].apply(set)
        coocurrencias = Counter()
        for prods in ordenes_con_prods:
            if len(prods) > 1:
                for combo in combinations(sorted(prods), 2):
                    coocurrencias[combo] += 1
        
        correlaciones = []
        for (p1, p2), count in coocurrencias.most_common():
            if count > 1:
                correlaciones.append({
                    "p1": p1,
                    "p2": p2,
                    "count": count
                })
            
        return {
            "kpi": kpi,
            "pareto": pareto,
            "anclas": anclas,
            "portafolio": portafolio,
            "correlaciones": correlaciones
        }

    data_store = {}
    data_store['total'] = analizar_sucursal(df)
    
    # Analyze by individual restaurant id
    restaurants = db.query(Restaurant).filter(Restaurant.company_id == current_user.company_id).all()
    for rest in restaurants:
        df_sucursal = df[df['SUCURSAL'] == str(rest.id)]
        if not df_sucursal.empty:
            data_store[str(rest.id)] = analizar_sucursal(df_sucursal)
            
    return data_store

@router.get("/sales/mappings")
def get_sales_mappings(db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    from models.models import POSSale, POSProductMapping
    
    # Distinct products from sales
    distinct_products = db.query(POSSale.product_name).filter(POSSale.company_id == current_user.company_id).distinct().all()
    
    # Current mappings
    mappings = db.query(POSProductMapping).filter(POSProductMapping.company_id == current_user.company_id).all()
    mapping_dict = {m.product_name: m for m in mappings}
    
    result = []
    for p in distinct_products:
        name = p.product_name
        if not name: continue
        m = mapping_dict.get(name)
        result.append({
            "product_name": name,
            "alternative_name": m.alternative_name if m else None,
            "category_name": m.category_name if m else "Uncategorized",
            "is_ignored": m.is_ignored if m else False
        })
    return sorted(result, key=lambda x: x["product_name"])

@router.post("/sales/mappings/bulk")
def update_sales_mappings(data: List[POSMappingBulkUpdate], db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    from models.models import POSProductMapping
    
    for item in data:
        product_name = item.product_name
        if not product_name: continue
        
        mapping = db.query(POSProductMapping).filter(
            POSProductMapping.company_id == current_user.company_id,
            POSProductMapping.product_name == product_name
        ).first()
        
        if mapping:
            mapping.alternative_name = item.alternative_name
            mapping.category_name = item.category_name or "Uncategorized"
            mapping.is_ignored = item.is_ignored
        else:
            mapping = POSProductMapping(
                company_id=current_user.company_id,
                product_name=product_name,
                alternative_name=item.alternative_name,
                category_name=item.category_name or "Uncategorized",
                is_ignored=item.is_ignored
            )
            db.add(mapping)
            
    db.commit()
    return {"message": "Mappings updated successfully"}

# ── NPS Management ──────────────────────────────────────────

@router.get("/nps/questions")
def get_nps_questions(db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    from models.models import NPSQuestion
    return db.query(NPSQuestion).filter(NPSQuestion.company_id == current_user.company_id).order_by(NPSQuestion.display_order).all()

@router.post("/nps/questions")
def create_nps_question(payload: NPSQuestionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    from models.models import NPSQuestion
    q = NPSQuestion(
        company_id=current_user.company_id,
        question_text=payload.question_text,
        question_type=payload.question_type,
        is_active=payload.is_active,
        display_order=payload.display_order
    )
    db.add(q)
    db.commit()
    return q

@router.put("/nps/questions/{qid}")
def update_nps_question(qid: int, payload: NPSQuestionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    from models.models import NPSQuestion
    q = db.query(NPSQuestion).filter(NPSQuestion.id == qid, NPSQuestion.company_id == current_user.company_id).first()
    if not q: raise HTTPException(404, "Question not found")
    q.question_text = payload.question_text
    q.question_type = payload.question_type
    q.is_active = payload.is_active
    q.display_order = payload.display_order
    db.commit()
    return q

@router.delete("/nps/questions/{qid}")
def delete_nps_question(qid: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    from models.models import NPSQuestion
    q = db.query(NPSQuestion).filter(NPSQuestion.id == qid, NPSQuestion.company_id == current_user.company_id).first()
    if not q: raise HTTPException(404, "Question not found")
    db.delete(q)
    db.commit()
    return {"message": "Deleted"}
