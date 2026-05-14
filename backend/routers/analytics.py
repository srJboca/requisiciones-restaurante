from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
from collections import Counter

from database import get_db, SessionLocal
from models.models import User, POSSale, Restaurant, POSProductMapping
from dependencies import get_current_company_admin, get_analytical_access
from utils.cache import analytics_cache
from fastapi import BackgroundTasks

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

def _preload_company_data(company_id: int):
    """
    Background task to warm up the cache for all individual restaurants.
    """
    db = SessionLocal()
    try:
        restaurants = db.query(Restaurant).filter(
            Restaurant.company_id == company_id, 
            Restaurant.is_active == True
        ).all()
        
        # Mock user for internal scoping
        mock_user = User(company_id=company_id, role='Business User', restaurant_id=None)
        
        for r in restaurants:
            # Trigger each report calculation for this restaurant (trigger_preload=False to avoid loops)
            get_traffic_matrices(restaurant_id=r.id, db=db, current_user=mock_user, trigger_preload=False)
            get_product_mix(restaurant_id=r.id, db=db, current_user=mock_user, trigger_preload=False)
            get_market_basket(restaurant_id=r.id, db=db, current_user=mock_user, trigger_preload=False)
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error during background preload: {e}")
    finally:
        db.close()

@router.get("/traffic-matrices")
def get_traffic_matrices(
    restaurant_id: int = None, 
    start_date: str = None, 
    end_date: str = None,
    trigger_preload: bool = True, 
    background_tasks: BackgroundTasks = None, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_analytical_access)
):
    import logging
    logging.getLogger(__name__).info(f"TRAFFIC REQ: rid={restaurant_id}, start={start_date}, end={end_date}")
    # Scope for Business User by restaurant
    if current_user.role == 'Business User' and current_user.restaurant_id:
        restaurant_id = current_user.restaurant_id

    cache_key = f"traffic_{current_user.company_id}_{restaurant_id}_{start_date}_{end_date}"
    cached = analytics_cache.get(cache_key)
    if cached: 
        if restaurant_id is None and trigger_preload and background_tasks:
            background_tasks.add_task(_preload_company_data, current_user.company_id)
        return cached

    query = db.query(POSSale).filter(POSSale.company_id == current_user.company_id)
    if start_date:
        query = query.filter(POSSale.date_open >= start_date)
    if end_date:
        query = query.filter(POSSale.date_open <= f"{end_date} 23:59:59")
    if restaurant_id:
        query = query.filter(POSSale.restaurant_id == restaurant_id)
    
    # Use pandas to read the query directly for performance
    df = pd.read_sql(query.statement, db.bind)
    
    if df.empty:
        return {
            "sales": {d: {h: 0 for h in range(24)} for d in range(7)},
            "diners": {d: {h: 0 for h in range(24)} for d in range(7)},
            "orders": {d: {h: 0 for h in range(24)} for d in range(7)},
            "top_product": {d: {h: "-" for h in range(24)} for d in range(7)},
            "hourly_traffic": [0]*24,
            "radar": [0]*7,
            "bubble": [],
            "kpis": {
                "total_sales": 0, "total_orders": 0, "avg_ticket": 0, "avg_diners": 0, "peak_hour": "--:--"
            }
        }

    # Helper: Convert date strings to datetime objects
    # Handle both date_open and date_close as needed. date_open is used for grouping by time.
    df['dt_open'] = pd.to_datetime(df['date_open'], errors='coerce')
    df = df.dropna(subset=['dt_open'])
    
    df['hour'] = df['dt_open'].dt.hour
    df['dow'] = df['dt_open'].dt.dayofweek # 0=Monday, 6=Sunday
    
    # KPIs
    total_sales = float(df['price_with_tax'].sum())
    total_orders = df['order_ref'].nunique()
    total_diners = int(df['diners'].sum())
    avg_ticket = total_sales / total_orders if total_orders > 0 else 0
    avg_diners = total_diners / total_orders if total_orders > 0 else 0

    # Hourly distribution
    hourly_counts = df.groupby('hour')['order_ref'].nunique()
    total_hourly_orders = hourly_counts.sum()
    hourly_traffic = [(float(hourly_counts.get(h, 0)) / total_hourly_orders * 100 if total_hourly_orders > 0 else 0) for h in range(24)]
    
    peak_hour = int(hourly_counts.idxmax()) if not hourly_counts.empty else 0

    # Weekly Radar (Orders by Day)
    radar_counts = df.groupby('dow')['order_ref'].nunique()
    radar_data = [int(radar_counts.get(d, 0)) for d in range(7)]

    # Heatmaps (Day x Hour)
    # 0=Monday...6=Sunday
    m_sales = {d: {h: 0 for h in range(24)} for d in range(7)}
    m_diners = {d: {h: 0 for h in range(24)} for d in range(7)}
    m_orders = {d: {h: 0 for h in range(24)} for d in range(7)}
    m_top = {d: {h: "-" for h in range(24)} for d in range(7)}

    # Group by dow and hour
    grouped = df.groupby(['dow', 'hour'])
    sales_agg = grouped['price_with_tax'].sum()
    diners_agg = grouped['diners'].sum()
    orders_agg = grouped['order_ref'].nunique()
    
    # Top product per slot
    top_prod_agg = grouped['product_name'].apply(lambda x: x.value_counts().index[0] if not x.empty else "-")

    for (d, h), val in sales_agg.items(): m_sales[int(d)][int(h)] = float(val)
    for (d, h), val in diners_agg.items(): m_diners[int(d)][int(h)] = int(val)
    for (d, h), val in orders_agg.items(): m_orders[int(d)][int(h)] = int(val)
    for (d, h), val in top_prod_agg.items(): m_top[int(d)][int(h)] = str(val)

    # Bubble Data (Orders vs Avg Ticket per Hour)
    bubble_df = df.groupby('hour').agg({
        'order_ref': 'nunique',
        'price_with_tax': 'sum'
    })
    bubble_data = []
    for h, row in bubble_df.iterrows():
        orders = int(row['order_ref'])
        if orders > 0:
            bubble_data.append({
                "x": int(h),
                "y": float(row['price_with_tax'] / orders),
                "orders": orders,
                "r": min(orders * 2, 30)
            })

    result = {
        "sales": m_sales, "diners": m_diners, "orders": m_orders, "top_product": m_top,
        "hourly_traffic": hourly_traffic, "radar": radar_data, "bubble": bubble_data,
        "kpis": {
            "total_sales": total_sales, "total_orders": total_orders,
            "avg_ticket": avg_ticket, "avg_diners": avg_diners, "peak_hour": f"{peak_hour:02d}:00"
        }
    }
    analytics_cache.set(cache_key, result)
    if restaurant_id is None and trigger_preload and background_tasks:
        background_tasks.add_task(_preload_company_data, current_user.company_id)
    return result

@router.get("/product-mix")
def get_product_mix(
    restaurant_id: int = None, 
    start_date: str = None, 
    end_date: str = None,
    trigger_preload: bool = True, 
    background_tasks: BackgroundTasks = None, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_analytical_access)
):
    import logging
    logging.getLogger(__name__).info(f"PRODMIX REQ: rid={restaurant_id}, start={start_date}, end={end_date}")
    # Scope for Business User by restaurant
    if current_user.role == 'Business User' and current_user.restaurant_id:
        restaurant_id = current_user.restaurant_id

    cache_key = f"prodmix_{current_user.company_id}_{restaurant_id}_{start_date}_{end_date}"
    cached = analytics_cache.get(cache_key)
    if cached: 
        if restaurant_id is None and trigger_preload and background_tasks:
            background_tasks.add_task(_preload_company_data, current_user.company_id)
        return cached

    query = db.query(POSSale).filter(POSSale.company_id == current_user.company_id)
    if start_date:
        query = query.filter(POSSale.date_open >= start_date)
    if end_date:
        query = query.filter(POSSale.date_open <= f"{end_date} 23:59:59")
    if restaurant_id:
        query = query.filter(POSSale.restaurant_id == restaurant_id)
    
    # Use pandas to read the query directly for performance
    df = pd.read_sql(query.statement, db.bind)
    
    if df.empty:
        return {"products": [], "categories": {}, "total_revenue": 0}

    # Get mappings
    mappings = db.query(POSProductMapping).filter(POSProductMapping.company_id == current_user.company_id).all()
    map_df = pd.DataFrame([
        {
            "product_name": m.product_name, 
            "strategic_name": m.alternative_name or m.product_name,
            "category": m.category_name or "Uncategorized",
            "is_ignored": m.is_ignored
        } for m in mappings
    ])

    if not map_df.empty:
        df = df.merge(map_df, on='product_name', how='left')
        # Fill defaults for unmapped products
        df['strategic_name'] = df['strategic_name'].fillna(df['product_name'])
        df['category'] = df['category'].fillna("Uncategorized")
        df['is_ignored'] = df['is_ignored'].fillna(False)
    else:
        df['strategic_name'] = df['product_name']
        df['category'] = "Uncategorized"
        df['is_ignored'] = False

    # Filter ignored products
    df = df[df['is_ignored'] == False]
    
    if df.empty:
        return {"products": [], "categories": {}, "total_revenue": 0}

    # Total revenue for percentages
    total_revenue = float(df['price_with_tax'].sum())

    # Product Stats
    prod_stats = df.groupby('strategic_name').agg({
        'category': 'first',
        'quantity': 'sum',
        'price_with_tax': 'sum'
    }).rename(columns={'quantity': 'qty', 'price_with_tax': 'revenue'})
    
    prod_stats['name'] = prod_stats.index
    prod_stats['pct_revenue'] = (prod_stats['revenue'] / total_revenue * 100) if total_revenue > 0 else 0

    # ABC Classification logic (vectorized)
    avg_rev = prod_stats['revenue'].mean()
    avg_qty = prod_stats['qty'].mean()
    
    prod_stats['classification'] = "Underperformer"
    prod_stats.loc[(prod_stats['revenue'] >= avg_rev) & (prod_stats['qty'] >= avg_qty), 'classification'] = "Star"
    prod_stats.loc[(prod_stats['revenue'] < avg_rev) & (prod_stats['qty'] >= avg_qty), 'classification'] = "Workhorse"
    prod_stats.loc[(prod_stats['revenue'] >= avg_rev) & (prod_stats['qty'] < avg_qty), 'classification'] = "Puzzle"

    # Category Stats
    cat_stats_df = df.groupby('category').agg({
        'quantity': 'sum',
        'price_with_tax': 'sum'
    }).rename(columns={'quantity': 'qty', 'price_with_tax': 'revenue'})
    cat_stats_df['name'] = cat_stats_df.index
    cat_stats = cat_stats_df.to_dict(orient='index')

    # Convert products to sorted list
    product_list = prod_stats.sort_values(by='revenue', ascending=False).to_dict(orient='records')

    result = {
        "products": product_list,
        "categories": cat_stats,
        "total_revenue": total_revenue
    }
    analytics_cache.set(cache_key, result)
    if restaurant_id is None and trigger_preload and background_tasks:
        background_tasks.add_task(_preload_company_data, current_user.company_id)
    return result

@router.get("/market-basket")
def get_market_basket(
    restaurant_id: int = None, 
    start_date: str = None, 
    end_date: str = None,
    trigger_preload: bool = True, 
    background_tasks: BackgroundTasks = None, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_analytical_access)
):
    import logging
    logging.getLogger(__name__).info(f"MKTBASKET REQ: rid={restaurant_id}, start={start_date}, end={end_date}")
    # Scope for Business User by restaurant
    if current_user.role == 'Business User' and current_user.restaurant_id:
        restaurant_id = current_user.restaurant_id

    query = db.query(POSSale).filter(POSSale.company_id == current_user.company_id)
    if restaurant_id:
        query = query.filter(POSSale.restaurant_id == restaurant_id)

    if start_date:
        query = query.filter(POSSale.date_open >= start_date)
    if end_date:
        query = query.filter(POSSale.date_open <= f"{end_date} 23:59:59")

    cache_key = f"mktbasket_{current_user.company_id}_{restaurant_id}_{start_date}_{end_date}"
    cached = analytics_cache.get(cache_key)
    if cached: 
        if restaurant_id is None and trigger_preload and background_tasks:
            background_tasks.add_task(_preload_company_data, current_user.company_id)
        return cached
    
    sales = query.all()
    if not sales:
        return {"pairs": [], "basket_dist": {}, "product_freq": {}}

    # Get mappings
    mappings = db.query(POSProductMapping).filter(POSProductMapping.company_id == current_user.company_id).all()
    mapping_dict = {m.product_name: (m.alternative_name or m.product_name) for m in mappings if not m.is_ignored}
    ignored_products = {m.product_name for m in mappings if m.is_ignored}

    # Group items by order_ref
    orders = {} # order_ref -> set of products
    product_freq = Counter() # product -> count of orders it appeared in
    total_orders = 0

    for s in sales:
        if s.product_name in ignored_products: continue
        if not s.order_ref: continue
        
        name = mapping_dict.get(s.product_name, s.product_name)
        if s.order_ref not in orders:
            orders[s.order_ref] = set()
            total_orders += 1
            
        if name not in orders[s.order_ref]:
            orders[s.order_ref].add(name)
            product_freq[name] += 1

    # Basket Size Distribution
    basket_sizes = [len(items) for items in orders.values()]
    basket_dist = Counter(basket_sizes)

    # Calculate Pairs (Support, Confidence, Lift)
    # We'll focus on the top 50 most frequent products to keep the matrix manageable
    top_prods = [p for p, f in product_freq.most_common(100)]
    pair_freq = Counter() # (p1, p2) -> count of orders both appeared in

    for items in orders.values():
        item_list = sorted([i for i in items if i in top_prods])
        for i in range(len(item_list)):
            for j in range(i + 1, len(item_list)):
                pair_freq[(item_list[i], item_list[j])] += 1

    pairs_result = []
    for (p1, p2), count in pair_freq.items():
        support = count / total_orders
        conf_p1_to_p2 = count / product_freq[p1]
        conf_p2_to_p1 = count / product_freq[p2]
        
        # Lift = P(A & B) / (P(A) * P(B))
        p_p1 = product_freq[p1] / total_orders
        p_p2 = product_freq[p2] / total_orders
        lift = support / (p_p1 * p_p2) if (p_p1 * p_p2) > 0 else 0
        
        if lift > 1.1: # Only include interesting correlations
            pairs_result.append({
                "p1": p1,
                "p2": p2,
                "support": support,
                "conf_1_2": conf_p1_to_p2,
                "conf_2_1": conf_p2_to_p1,
                "lift": lift,
                "frequency": count
            })

    # Sort by lift descending
    pairs_result.sort(key=lambda x: x["lift"], reverse=True)

    result = {
        "pairs": pairs_result[:500], # Limit results
        "product_freq": dict(product_freq),
        "basket_dist": dict(basket_dist),
        "total_orders": total_orders
    }
    analytics_cache.set(cache_key, result)
    if restaurant_id is None and trigger_preload and background_tasks:
        background_tasks.add_task(_preload_company_data, current_user.company_id)
    return result
