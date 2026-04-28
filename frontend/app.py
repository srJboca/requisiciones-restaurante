import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import requests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "frontendsecret_change_in_production")
API_URL = os.environ.get("API_URL", "http://backend:8000")
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "http://localhost:8000")

def get_auth_headers():
    token = session.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

@app.route("/")
def welcome():
    if "access_token" in session:
        if session.get("role") == "Admin":
            return redirect(url_for("admin_dashboard"))
        elif session.get("role") == "Restaurant":
            return redirect(url_for("restaurant_order"))
        elif session.get("role") == "Production Plant":
            return redirect(url_for("production_shipping"))
    return render_template("welcome.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        try:
            res = requests.post(f"{API_URL}/auth/login", data={"username": username, "password": password})
            if res.status_code == 200:
                data = res.json()
                session["access_token"] = data["access_token"]
                session["role"] = data["role"]
                return redirect(url_for("welcome"))
            else:
                flash("Invalid credentials", "danger")
        except Exception as e:
            flash(f"Connection error: {e}", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

@app.route("/restaurant/order")
def restaurant_order():
    if session.get("role") != "Restaurant":
        return redirect(url_for("welcome"))
    
    headers = get_auth_headers()
    selected_date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    
    try:
        # Fetch product groups
        res = requests.get(f"{API_URL}/requisitions/product-groups", headers=headers)
        groups = res.json() if res.status_code == 200 else []
        
        # Fetch products
        res = requests.get(f"{API_URL}/requisitions/products", headers=headers)
        products = res.json() if res.status_code == 200 else []

        # Fetch active order for selected date
        res = requests.get(f"{API_URL}/requisitions/active?date={selected_date}", headers=headers)
        today_order = res.json() if res.status_code == 200 else {"status": "None", "items": []}

        # Fetch report orders
        res = requests.get(f"{API_URL}/requisitions/report", headers=headers)
        report_orders = res.json() if res.status_code == 200 else []

        # Fetch ETA Days
        res = requests.get(f"{API_URL}/requisitions/eta-days", headers=headers)
        eta_days = res.json().get('eta_days', 2) if res.status_code == 200 else 2
    except:
        groups, products, today_order, report_orders = [], [], {"status": "None", "items": []}, []
        eta_days = 2

    # Map items for easy lookup in template
    today_items_map = {item['product_id']: item for item in today_order.get('items', [])}

    return render_template("restaurant_order.html", 
                           groups=groups, products=products, 
                           today_order=today_order, today_items=today_items_map, 
                           report_orders=report_orders, selected_date=selected_date, 
                           eta_days=eta_days, API_URL=PUBLIC_API_URL)

@app.route("/restaurant/receiving")
def restaurant_receiving():
    if session.get("role") != "Restaurant":
        return redirect(url_for("welcome"))
    
    headers = get_auth_headers()
    date_filter = request.args.get("order_date", "")
    
    try:
        url = f"{API_URL}/requisitions/shipped"
        if date_filter:
            url += f"?order_date={date_filter}"
        res = requests.get(url, headers=headers)
        orders = res.json() if res.status_code == 200 else []
    except:
        orders = []

    return render_template("restaurant_receiving.html", orders=orders, API_URL=PUBLIC_API_URL)

@app.route("/production/shipping")
def production_shipping():
    if session.get("role") != "Production Plant":
        return redirect(url_for("welcome"))
    
    headers = get_auth_headers()
    date_filter = request.args.get("order_date", "")
    
    try:
        url = f"{API_URL}/production/requirements"
        if date_filter:
            url += f"?order_date={date_filter}"
        res = requests.get(url, headers=headers)
        orders = res.json() if res.status_code == 200 else []
    except:
        orders = []

    return render_template("production_shipping.html", orders=orders, API_URL=PUBLIC_API_URL)

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "Admin":
        return redirect(url_for("welcome"))
    
    headers = get_auth_headers()
    try:
        users = requests.get(f"{API_URL}/admin/users", headers=headers).json()
        restaurants = requests.get(f"{API_URL}/admin/restaurants", headers=headers).json()
        groups = requests.get(f"{API_URL}/admin/product-groups", headers=headers).json()
        products = requests.get(f"{API_URL}/admin/products", headers=headers).json()
        logs = requests.get(f"{API_URL}/admin/audit-logs", headers=headers).json()
        
        eta_res = requests.get(f"{API_URL}/admin/settings", headers=headers)
        eta_days = eta_res.json().get("eta_days", "2") if eta_res.status_code == 200 else "2"
    except:
        users, restaurants, groups, products, logs = [], [], [], [], []
        eta_days = "2"

    return render_template("admin_dashboard.html", users=users, restaurants=restaurants, groups=groups, products=products, logs=logs, eta_days=eta_days, API_URL=PUBLIC_API_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
