"""
Production Plant router — scoped to the current user's assigned production plant.
Only shows orders from restaurants assigned to this production plant.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from database import get_db
from models.models import User, Order, OrderItem, Restaurant
from dependencies import get_current_production, log_audit

router = APIRouter(prefix="/production", tags=["production"])

class OrderShipItem(BaseModel):
    order_item_id: int
    shipped_quantity: float

class OrderShip(BaseModel):
    items: List[OrderShipItem]
    production_notes: str | None = None

def _plant_restaurant_ids(db: Session, current_user: User) -> list[int]:
    """Return IDs of all restaurants assigned to the current user's production plant."""
    if not current_user.production_plant_id:
        return []
    rests = db.query(Restaurant).filter(
        Restaurant.production_plant_id == current_user.production_plant_id,
        Restaurant.company_id == current_user.company_id
    ).all()
    return [r.id for r in rests]

@router.get("/requirements")
def get_requirements(
    order_date: str | None = None,
    restaurant_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_production)
):
    """Orders in 'Submitted' status directed to this production plant."""
    plant_rest_ids = _plant_restaurant_ids(db, current_user)
    if not plant_rest_ids:
        return []

    query = db.query(Order).filter(
        Order.status == 'Submitted',
        Order.restaurant_id.in_(plant_rest_ids)
    )
    if order_date:
        query = query.filter(Order.order_date == order_date)
    if restaurant_id and restaurant_id in plant_rest_ids:
        query = query.filter(Order.restaurant_id == restaurant_id)

    result = []
    for o in query.all():
        items = [
            {
                "item_id": i.id,
                "product_id": i.product_id,
                "product_name": i.product.name,
                "sku": i.product.sku,
                "unit_measure": i.product.unit_measure,
                "required_quantity": float(i.required_quantity),
                "current_inventory": float(i.current_inventory),
            }
            for i in o.items if i.required_quantity > 0
        ]
        if items:
            result.append({
                "order_id": o.id,
                "restaurant_name": o.restaurant.name,
                "order_date": o.order_date,
                "restaurant_notes": o.restaurant_notes,
                "items": items,
                "submitted_by_name": o.submitted_by.username if o.submitted_by else None,
            })
    return result

@router.post("/{order_id}/ship")
def ship_order(
    order_id: int,
    ship_data: OrderShip,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_production)
):
    plant_rest_ids = _plant_restaurant_ids(db, current_user)
    order = db.query(Order).filter(Order.id == order_id, Order.restaurant_id.in_(plant_rest_ids)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found or not assigned to your production plant")
    if order.status != 'Submitted':
        raise HTTPException(status_code=400, detail="Order is not in Submitted status")

    for item_data in ship_data.items:
        item = db.query(OrderItem).filter(OrderItem.id == item_data.order_item_id, OrderItem.order_id == order.id).first()
        if item:
            item.shipped_quantity = item_data.shipped_quantity

    order.status = 'Shipped'
    order.shipped_by_id = current_user.id
    order.production_notes = ship_data.production_notes
    db.commit()
    log_audit(db, current_user.id, "Ship Order", "Order", order.id, f"Shipped order {order.id}")
    return {"message": "Order shipped successfully"}

@router.get("/history")
def get_history(
    order_date: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_production)
):
    """All non-draft orders for restaurants assigned to this production plant."""
    plant_rest_ids = _plant_restaurant_ids(db, current_user)
    if not plant_rest_ids:
        return []

    query = db.query(Order).filter(
        Order.status != 'Draft',
        Order.restaurant_id.in_(plant_rest_ids)
    ).order_by(Order.order_date.desc())
    if order_date:
        query = query.filter(Order.order_date == order_date)

    result = []
    for o in query.all():
        result.append({
            "order_id": o.id,
            "restaurant_name": o.restaurant.name if o.restaurant else "Unknown",
            "order_date": o.order_date,
            "status": o.status,
            "submitted_by_name": o.submitted_by.username if o.submitted_by else None,
            "shipped_by_name": o.shipped_by.username if o.shipped_by else None,
            "received_by_name": o.received_by.username if o.received_by else None,
            "restaurant_notes": o.restaurant_notes,
            "production_notes": o.production_notes,
            "receiving_notes": o.receiving_notes,
            "items": [{
                "item_id": i.id, "product_name": i.product.name, "sku": i.product.sku,
                "required_quantity": float(i.required_quantity),
                "shipped_quantity": float(i.shipped_quantity) if i.shipped_quantity else 0,
                "received_quantity": float(i.received_quantity) if i.received_quantity else 0,
            } for i in o.items]
        })
    return result
