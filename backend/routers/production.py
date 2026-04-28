from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.models import User, Order, OrderItem, Restaurant, Product, ProductGroup
from dependencies import get_current_production, log_audit
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/production", tags=["production"], dependencies=[Depends(get_current_production)])

class OrderShipItem(BaseModel):
    order_item_id: int
    shipped_quantity: float

class OrderShip(BaseModel):
    items: List[OrderShipItem]

@router.get("/requirements")
def get_requirements(order_date: str | None = None, restaurant_id: int | None = None, group_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Order).filter(Order.status == 'Submitted')
    if order_date:
        query = query.filter(Order.order_date == order_date)
    if restaurant_id:
        query = query.filter(Order.restaurant_id == restaurant_id)
        
    orders = query.all()
    result = []
    
    for o in orders:
        items = []
        for i in o.items:
            # Only include if required_quantity > 0
            if i.required_quantity > 0:
                if group_id and i.product.group_id != group_id:
                    continue
                items.append({
                    "item_id": i.id,
                    "product_id": i.product_id,
                    "product_name": i.product.name,
                    "sku": i.product.sku,
                    "required_quantity": float(i.required_quantity),
                    "current_inventory": float(i.current_inventory)
                })
        if items:
            result.append({
                "order_id": o.id,
                "restaurant_name": o.restaurant.name,
                "order_date": o.order_date,
                "items": items,
                "submitted_by_name": o.submitted_by.username if o.submitted_by else None
            })
    return result

@router.post("/{order_id}/ship")
def ship_order(order_id: int, ship_data: OrderShip, db: Session = Depends(get_db), current_user: User = Depends(get_current_production)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != 'Submitted':
        raise HTTPException(status_code=400, detail="Order is not in Submitted status")

    for item_data in ship_data.items:
        item = db.query(OrderItem).filter(OrderItem.id == item_data.order_item_id, OrderItem.order_id == order.id).first()
        if item:
            item.shipped_quantity = item_data.shipped_quantity

    order.status = 'Shipped'
    order.shipped_by_id = current_user.id
    db.commit()
    log_audit(db, current_user.id, "Ship Order", "Order", order.id, f"Shipped order {order.id}")
    return {"message": "Order shipped successfully"}

@router.get("/history")
def get_history(order_date: str | None = None, restaurant_id: int | None = None, db: Session = Depends(get_db)):
    # Production sees all non-draft orders
    query = db.query(Order).filter(Order.status != 'Draft').order_by(Order.order_date.desc())
    if order_date:
        query = query.filter(Order.order_date == order_date)
    if restaurant_id:
        query = query.filter(Order.restaurant_id == restaurant_id)
        
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
                "required_quantity": float(i.required_quantity),
                "shipped_quantity": float(i.shipped_quantity) if i.shipped_quantity is not None else 0,
                "received_quantity": float(i.received_quantity) if i.received_quantity is not None else 0
            })
        result.append({
            "order_id": o.id,
            "restaurant_name": o.restaurant.name if o.restaurant else "Unknown",
            "order_date": o.order_date,
            "status": o.status,
            "items": items,
            "submitted_by_name": o.submitted_by.username if o.submitted_by else None,
            "shipped_by_name": o.shipped_by.username if o.shipped_by else None,
            "received_by_name": o.received_by.username if o.received_by else None
        })
    return result
