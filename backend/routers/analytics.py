from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from collections import Counter

from database import get_db
from models.models import User, POSSale, Restaurant, POSProductMapping
from dependencies import get_current_company_admin

router = APIRouter(prefix="/admin/analytics", tags=["analytics"])

def parse_date(date_str):
    if not date_str:
        return None
    # Try common formats
    for fmt in ("%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None

@router.get("/traffic-matrices")
def get_traffic_matrices(restaurant_id: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    query = db.query(POSSale).filter(POSSale.company_id == current_user.company_id)
    if restaurant_id:
        query = query.filter(POSSale.restaurant_id == restaurant_id)
    
    sales = query.all()
    if not sales:
        return {
            "sales": {},
            "diners": {},
            "orders": {},
            "top_product": {},
            "hourly_traffic": [0]*24
        }

    # Get mappings for names
    mappings = db.query(POSProductMapping).filter(POSProductMapping.company_id == current_user.company_id).all()
    mapping_dict = {m.product_name: (m.alternative_name or m.product_name) for m in mappings if not m.is_ignored}
    ignored_products = {m.product_name for m in mappings if m.is_ignored}

    # Matrices: weekday (0=Mon, 6=Sun) -> hour (0-23)
    m_sales = {d: {h: 0.0 for h in range(24)} for d in range(7)}
    m_diners = {d: {h: [] for h in range(24)} for d in range(7)}
    m_orders = {d: {h: set() for h in range(24)} for d in range(7)}
    m_top_prod = {d: {h: Counter() for h in range(24)} for d in range(7)}
    hourly_traffic = Counter()
    
    # Radar Data: volume per day
    radar_data = [0]*7
    
    # Bubble & Scatter Data
    # We'll group by order_ref to get true average tickets
    order_data = {} # order_ref -> {sales, diners, hour, weekday}

    for s in sales:
        if s.product_name in ignored_products: continue
        dt = parse_date(s.date_open)
        if not dt: continue
        d, h = dt.weekday(), dt.hour
        
        m_sales[d][h] += float(s.price_with_tax or 0)
        m_diners[d][h].append(int(s.diners or 0))
        if s.order_ref:
            m_orders[d][h].add(s.order_ref)
            if s.order_ref not in order_data:
                order_data[s.order_ref] = {"sales": 0, "diners": int(s.diners or 0), "hour": h, "weekday": d}
            order_data[s.order_ref]["sales"] += float(s.price_with_tax or 0)
        
        display_name = mapping_dict.get(s.product_name, s.product_name)
        m_top_prod[d][h][display_name] += int(s.quantity or 1)
        hourly_traffic[h] += 1
        radar_data[d] += 1

    # Finalize matrices
    final_diners = {d: {h: (sum(m_diners[d][h])/len(m_diners[d][h]) if m_diners[d][h] else 0) for h in range(24)} for d in range(7)}
    final_orders = {d: {h: len(m_orders[d][h]) for h in range(24)} for d in range(7)}
    final_top_prod = {d: {h: (m_top_prod[d][h].most_common(1)[0][0] if m_top_prod[d][h] else "-") for h in range(24)} for d in range(7)}
    
    # KPIs
    total_sales = sum(o["sales"] for o in order_data.values())
    total_orders = len(order_data)
    avg_ticket = total_sales / total_orders if total_orders > 0 else 0
    total_diners = sum(o["diners"] for o in order_data.values())
    avg_diners = total_diners / total_orders if total_orders > 0 else 0
    
    peak_hour = hourly_traffic.most_common(1)[0][0] if hourly_traffic else 0
    
    # Bubble Data: grouped by hour
    bubble_raw = {h: {"sales": 0, "orders": 0} for h in range(24)}
    for o in order_data.values():
        bubble_raw[o["hour"]]["sales"] += o["sales"]
        bubble_raw[o["hour"]]["orders"] += 1
    
    bubble_data = []
    for h, vals in bubble_raw.items():
        if vals["orders"] > 0:
            bubble_data.append({
                "x": h,
                "y": vals["sales"] / vals["orders"],
                "orders": vals["orders"], # Provide raw count
                "r": min(vals["orders"] * 2, 30) # Keep for compat but use .orders in JS
            })

    return {
        "sales": m_sales,
        "diners": final_diners,
        "orders": final_orders,
        "top_product": final_top_prod,
        "hourly_traffic": [ (hourly_traffic[h] / sum(hourly_traffic.values()) * 100 if sum(hourly_traffic.values()) > 0 else 0) for h in range(24) ],
        "radar": radar_data,
        "bubble": bubble_data,
        "kpis": {
            "total_sales": total_sales,
            "total_orders": total_orders,
            "avg_ticket": avg_ticket,
            "avg_diners": avg_diners,
            "peak_hour": f"{peak_hour}:00"
        }
    }

@router.get("/product-mix")
def get_product_mix(restaurant_id: int = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_company_admin)):
    query = db.query(POSSale).filter(POSSale.company_id == current_user.company_id)
    if restaurant_id:
        query = query.filter(POSSale.restaurant_id == restaurant_id)
    
    sales = query.all()
    if not sales:
        return {"products": [], "categories": {}, "total_revenue": 0}

    # Get mappings
    mappings = db.query(POSProductMapping).filter(POSProductMapping.company_id == current_user.company_id).all()
    mapping_dict = {m.product_name: {"name": (m.alternative_name or m.product_name), "category": (m.category_name or "Uncategorized")} for m in mappings if not m.is_ignored}
    ignored_products = {m.product_name for m in mappings if m.is_ignored}

    prod_stats = {} # name -> {qty, revenue, category}
    cat_stats = {} # name -> {qty, revenue}
    total_revenue = 0

    for s in sales:
        if s.product_name in ignored_products: continue
        
        info = mapping_dict.get(s.product_name, {"name": s.product_name, "category": "Uncategorized"})
        name = info["name"]
        cat = info["category"]
        qty = int(s.quantity or 1)
        rev = float(s.price_with_tax or 0)
        
        total_revenue += rev
        
        if name not in prod_stats:
            prod_stats[name] = {"name": name, "category": cat, "qty": 0, "revenue": 0}
        prod_stats[name]["qty"] += qty
        prod_stats[name]["revenue"] += rev

        if cat not in cat_stats:
            cat_stats[cat] = {"name": cat, "qty": 0, "revenue": 0}
        cat_stats[cat]["qty"] += qty
        cat_stats[cat]["revenue"] += rev

    # Convert and calculate classifications
    product_list = list(prod_stats.values())
    if product_list:
        avg_rev = sum(p["revenue"] for p in product_list) / len(product_list)
        avg_qty = sum(p["qty"] for p in product_list) / len(product_list)
        
        for p in product_list:
            p["pct_revenue"] = (p["revenue"] / total_revenue * 100) if total_revenue > 0 else 0
            # Classification logic
            if p["revenue"] >= avg_rev and p["qty"] >= avg_qty: p["classification"] = "Star"
            elif p["revenue"] < avg_rev and p["qty"] >= avg_qty: p["classification"] = "Workhorse"
            elif p["revenue"] >= avg_rev and p["qty"] < avg_qty: p["classification"] = "Puzzle"
            else: p["classification"] = "Underperformer"

    # Sort products by revenue descending
    product_list.sort(key=lambda x: x["revenue"], reverse=True)

    return {
        "products": product_list,
        "categories": cat_stats,
        "total_revenue": total_revenue
    }
