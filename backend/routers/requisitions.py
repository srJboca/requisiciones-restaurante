from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import get_db
from models.models import User, Order, OrderItem, Product, ProductGroup, SystemSetting
from dependencies import get_current_restaurant, log_audit
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/requisitions", tags=["requisitions"], dependencies=[Depends(get_current_restaurant)])

class OrderItemCreate(BaseModel):
    product_id: int
    current_inventory: float
    required_quantity: float

class OrderCreate(BaseModel):
    order_date: str
    items: List[OrderItemCreate]

class OrderSend(BaseModel):
    order_date: str

class OrderReceiveItem(BaseModel):
    order_item_id: int
    received_quantity: float

class OrderReceive(BaseModel):
    items: List[OrderReceiveItem]

@router.get("/product-groups")
def get_product_groups(db: Session = Depends(get_db)):
    return db.query(ProductGroup).all()

@router.get("/products")
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.is_active == True).all()

def add_business_days(start_date: datetime, days: int) -> datetime:
    current_date = start_date
    while days > 0:
        current_date += timedelta(days=1)
        if current_date.weekday() < 5: # 0-4 are Monday-Friday
            days -= 1
    return current_date

@router.get("/eta-days")
def get_eta_days(db: Session = Depends(get_db)):
    setting = db.query(SystemSetting).filter(SystemSetting.setting_key == 'eta_days').first()
    return {"eta_days": int(setting.setting_value) if setting else 2}

@router.get("/active")
def get_active_order(date: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_restaurant)):
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a restaurant")
    
    order_date = date if date else datetime.now().strftime("%Y-%m-%d")
    order = db.query(Order).filter(
        Order.restaurant_id == current_user.restaurant_id,
        Order.order_date == order_date
    ).first()
    
    if not order:
        return {"status": "None", "items": [], "delivery_date": None}
        
    items = []
    for i in order.items:
        items.append({
            "product_id": i.product_id, 
            "required_quantity": float(i.required_quantity), 
            "current_inventory": float(i.current_inventory),
            "edited_by_name": i.edited_by.username if i.edited_by else None
        })
    return {
        "status": order.status, 
        "items": items, 
        "order_id": order.id, 
        "delivery_date": order.delivery_date,
        "submitted_by_name": order.submitted_by.username if order.submitted_by else None,
        "shipped_by_name": order.shipped_by.username if order.shipped_by else None,
        "received_by_name": order.received_by.username if order.received_by else None
    }

@router.post("/draft")
def save_draft(order_data: OrderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_restaurant)):
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a restaurant")
    
    order_date = order_data.order_date
    
    order = db.query(Order).filter(
        Order.restaurant_id == current_user.restaurant_id,
        Order.order_date == order_date
    ).first()
    
    if order and order.status != 'Draft':
        raise HTTPException(status_code=400, detail="Order has already been sent to production")
        
    if not order:
        order = Order(restaurant_id=current_user.restaurant_id, order_date=order_date, status='Draft')
        db.add(order)
        db.commit()
        db.refresh(order)
    else:
        db.query(OrderItem).filter(OrderItem.order_id == order.id).delete()
        db.commit()
        
    for item in order_data.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            current_inventory=item.current_inventory,
            required_quantity=item.required_quantity,
            edited_by_id=current_user.id
        )
        db.add(order_item)
    
    db.commit()
    log_audit(db, current_user.id, "Save Draft", "Order", order.id, f"Saved draft for {order_date}")
    return {"message": "Draft saved successfully", "order_id": order.id}

@router.post("/send")
def send_order(send_data: OrderSend, db: Session = Depends(get_db), current_user: User = Depends(get_current_restaurant)):
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a restaurant")
        
    order_date = send_data.order_date
    order = db.query(Order).filter(
        Order.restaurant_id == current_user.restaurant_id,
        Order.order_date == order_date
    ).first()
    
    if not order or order.status != 'Draft':
        raise HTTPException(status_code=400, detail="No draft found or order is already sent")
        
    # Calculate ETA
    setting = db.query(SystemSetting).filter(SystemSetting.setting_key == 'eta_days').first()
    eta_days = int(setting.setting_value) if setting else 2
    
    start_dt = datetime.strptime(order_date, "%Y-%m-%d")
    delivery_dt = add_business_days(start_dt, eta_days)
    
    order.delivery_date = delivery_dt.strftime("%Y-%m-%d")
    order.status = 'Submitted'
    order.submitted_by_id = current_user.id
    db.commit()
    log_audit(db, current_user.id, "Send Order", "Order", order.id, f"Sent order to production for {order_date} with ETA {order.delivery_date}")
    return {"message": "Order sent to production", "delivery_date": order.delivery_date}

@router.get("/report")
def get_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_restaurant)):
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a restaurant")
        
    orders = db.query(Order).filter(Order.restaurant_id == current_user.restaurant_id).order_by(Order.order_date.desc()).all()
    result = []
    for o in orders:
        result.append({
            "order_id": o.id,
            "order_date": o.order_date,
            "status": o.status,
            "total_items": len(o.items),
            "delivery_date": o.delivery_date,
            "submitted_by_name": o.submitted_by.username if o.submitted_by else None,
            "shipped_by_name": o.shipped_by.username if o.shipped_by else None,
            "received_by_name": o.received_by.username if o.received_by else None
        })
    return result

@router.get("/shipped")
def get_shipped_orders(order_date: str | None = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_restaurant)):
    if not current_user.restaurant_id:
        raise HTTPException(status_code=400, detail="User is not assigned to a restaurant")

    query = db.query(Order).filter(Order.restaurant_id == current_user.restaurant_id, Order.status == 'Shipped')
    if order_date:
        query = query.filter(Order.order_date == order_date)
    
    orders = query.all()
    result = []
    for o in orders:
        items = []
        for i in o.items:
            items.append({
                "item_id": i.id,
                "product_id": i.product_id,
                "product_name": i.product.name,
                "sku": i.product.sku,
                "shipped_quantity": float(i.shipped_quantity) if i.shipped_quantity is not None else 0
            })
        result.append({
            "order_id": o.id,
            "order_date": o.order_date,
            "items": items,
            "shipped_by_name": o.shipped_by.username if o.shipped_by else None
        })
    return result

@router.post("/{order_id}/receive")
def receive_order(order_id: int, receive_data: OrderReceive, db: Session = Depends(get_db), current_user: User = Depends(get_current_restaurant)):
    order = db.query(Order).filter(Order.id == order_id, Order.restaurant_id == current_user.restaurant_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != 'Shipped':
        raise HTTPException(status_code=400, detail="Order is not in Shipped status")

    for item_data in receive_data.items:
        item = db.query(OrderItem).filter(OrderItem.id == item_data.order_item_id, OrderItem.order_id == order.id).first()
        if item:
            item.received_quantity = item_data.received_quantity

    order.status = 'Closed'
    order.received_by_id = current_user.id
    db.commit()
    log_audit(db, current_user.id, "Receive Order", "Order", order.id, f"Received order {order.id}")
    return {"message": "Order closed successfully"}
