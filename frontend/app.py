import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import requests
from flask_babel import Babel, gettext as _

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "frontendsecret_change_in_production")
API_URL = os.environ.get("API_URL", "http://backend:8000")
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "http://localhost:8000")

ADMIN_ROLES = {"CompanyAdmin", "Admin"}  # "Admin" kept for backward compat

def get_locale():
    if "lang" in session:
        return session["lang"]
    try:
        role = session.get("role", "")
        if role in ADMIN_ROLES:
            headers = get_auth_headers()
            res = requests.get(f"{API_URL}/admin/settings", headers=headers)
            if res.status_code == 200:
                return res.json().get("default_language", "en")
    except:
        pass
    return "en"

babel = Babel(app, locale_selector=get_locale)

@app.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in ["en", "es"]:
        session["lang"] = lang
    return redirect(request.referrer or url_for("welcome"))

def get_auth_headers():
    token = session.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}

# ── Root & Auth ──────────────────────────────────────────────

@app.route("/")
def welcome():
    if "access_token" in session:
        role = session.get("role")
        if role == "SuperAdmin":
            return redirect(url_for("superadmin_dashboard"))
        elif role in ADMIN_ROLES:
            return redirect(url_for("admin_dashboard"))
        elif role == "Restaurant":
            # Check subrole for NPS redirection
            if session.get("subrole") == "NPS":
                return redirect(url_for("nps_survey"))
            
            # Fallback/verification
            headers = get_auth_headers()
            try:
                profile = requests.get(f"{API_URL}/auth/me", headers=headers).json()
                if profile.get("subrole") == "NPS":
                    session["subrole"] = "NPS" # Ensure session is in sync
                    
                # Update branding in session if available
                branding = profile.get("branding", {})
                if branding.get("brand_name"):
                    session["brand_name"] = branding.get("brand_name")
                if branding.get("primary_color"):
                    session["primary_color"] = branding.get("primary_color")
                if branding.get("logo_url"):
                    session["logo_url"] = branding.get("logo_url")
                    
                if profile.get("subrole") == "NPS":
                    return redirect(url_for("nps_survey"))
            except:
                pass
            return redirect(url_for("restaurant_order"))
        elif role == "Production Plant":
            return redirect(url_for("production_shipping"))
    return render_template("welcome.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    try:
        res_setup = requests.get(f"{API_URL}/auth/setup-status", timeout=2)
        if res_setup.status_code == 200 and res_setup.json().get("setup_required"):
            return redirect(url_for("setup_wizard"))
    except:
        pass  # If backend unreachable, fall through to show login error

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            res = requests.post(f"{API_URL}/auth/login", data={"username": username, "password": password})
            if res.status_code == 200:
                data = res.json()
                session["access_token"] = data["access_token"]
                session["role"] = data["role"]
                session["subrole"] = data.get("subrole", "Requisition")
                session["company_id"] = data.get("company_id")
                
                branding = data.get("branding", {})
                session["brand_name"] = branding.get("brand_name")
                session["primary_color"] = branding.get("primary_color")
                session["logo_url"] = branding.get("logo_url")
                
                return redirect(url_for("welcome"))
            else:
                try:
                    detail = res.json().get("detail", "Invalid credentials")
                except ValueError:
                    detail = f"Server error ({res.status_code}): Backend is currently unavailable."
                flash(detail, "danger")
        except Exception as e:
            flash(f"Connection error: {e}", "danger")
    return render_template("login.html", API_URL=PUBLIC_API_URL)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

@app.route("/setup", methods=["GET", "POST"])
def setup_wizard():
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if password != confirm:
            flash(_("Passwords do not match"), "danger")
            return render_template("setup.html")
        
        try:
            res = requests.post(f"{API_URL}/auth/setup", json={"password": password})
            if res.status_code == 200:
                flash(_("Setup complete. You can now log in as superadmin."), "success")
                return redirect(url_for("login"))
            else:
                flash(res.json().get("detail", "Error during setup"), "danger")
        except Exception as e:
            flash(f"Connection error: {e}", "danger")
            
    return render_template("setup.html")

# ── SuperAdmin ───────────────────────────────────────────────

@app.route("/superadmin/dashboard")
def superadmin_dashboard():
    if session.get("role") != "SuperAdmin":
        return redirect(url_for("welcome"))
    headers = get_auth_headers()
    try:
        companies = requests.get(f"{API_URL}/superadmin/companies", headers=headers).json()
        settings = requests.get(f"{API_URL}/superadmin/settings", headers=headers).json()
    except:
        companies, settings = [], {}
    return render_template("superadmin_dashboard.html", companies=companies, settings=settings, API_URL=PUBLIC_API_URL)

# ── CompanyAdmin ─────────────────────────────────────────────

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") not in ADMIN_ROLES:
        return redirect(url_for("welcome"))
    headers = get_auth_headers()
    try:
        users = requests.get(f"{API_URL}/admin/users", headers=headers).json()
        restaurants = requests.get(f"{API_URL}/admin/restaurants", headers=headers).json()
        plants = requests.get(f"{API_URL}/admin/production-plants", headers=headers).json()
        groups = requests.get(f"{API_URL}/admin/product-groups", headers=headers).json()
        products = requests.get(f"{API_URL}/admin/products", headers=headers).json()
        logs = requests.get(f"{API_URL}/admin/audit-logs", headers=headers).json()
        nps_questions = requests.get(f"{API_URL}/admin/nps/questions", headers=headers).json()
        settings_res = requests.get(f"{API_URL}/admin/settings", headers=headers)
        settings = settings_res.json() if settings_res.status_code == 200 else {}
        eta_days = settings.get("eta_days", "2")
        default_language = settings.get("default_language", "en")
        nps_thank_you_message = settings.get("nps_thank_you_message", "Your feedback has been successfully recorded.")
        brand_name = settings.get("brand_name", "")
        primary_color = settings.get("primary_color", "#2563eb")
        logo_url = settings.get("logo_url", "")
        terms_and_conditions_url = settings.get("terms_and_conditions_url", "")
    except:
        users, restaurants, plants, groups, products, logs, nps_questions = [], [], [], [], [], [], []
        eta_days, default_language, nps_thank_you_message = "2", "en", ""
        brand_name, primary_color, logo_url, terms_and_conditions_url = "", "#2563eb", "", ""
    return render_template("admin_dashboard.html",
                           users=users, restaurants=restaurants, plants=plants,
                           groups=groups, products=products, logs=logs,
                           eta_days=eta_days, default_language=default_language,
                           nps_thank_you_message=nps_thank_you_message,
                           brand_name=brand_name, primary_color=primary_color, 
                           logo_url=logo_url, terms_and_conditions_url=terms_and_conditions_url,
                           nps_questions=nps_questions, API_URL=PUBLIC_API_URL)

@app.route("/nps/survey")
def nps_survey():
    if session.get("role") != "Restaurant":
        return redirect(url_for("welcome"))
    headers = get_auth_headers()
    try:
        data = requests.get(f"{API_URL}/nps/survey-questions", headers=headers).json()
        questions = data.get("questions", [])
        thank_you_message = data.get("thank_you_message", "Your feedback has been successfully recorded.")
        branding = data.get("branding", {})
        brand_name = branding.get("brand_name", "")
        primary_color = branding.get("primary_color", "#2563eb")
        logo_url = branding.get("logo_url", "")
        terms_and_conditions_url = data.get("terms_and_conditions_url", "")
    except:
        questions = []
        thank_you_message = "Your feedback has been successfully recorded."
        brand_name, primary_color, logo_url, terms_and_conditions_url = "", "#2563eb", "", ""
    return render_template("nps_survey.html", 
                           questions=questions, 
                           thank_you_message=thank_you_message, 
                           brand_name=brand_name,
                           primary_color=primary_color,
                           logo_url=logo_url,
                           terms_and_conditions_url=terms_and_conditions_url,
                           API_URL=PUBLIC_API_URL)

@app.route("/admin/reports/nps")
def admin_nps_report():
    if session.get("role") not in ["CompanyAdmin", "Admin", "SuperAdmin"]:
        return redirect(url_for("welcome"))
    
    restaurant_id = request.args.get("restaurant_id")
    headers = get_auth_headers()
    
    try:
        restaurants = requests.get(f"{API_URL}/admin/restaurants", headers=headers).json()
        report_url = f"{API_URL}/nps/report"
        if restaurant_id:
            report_url += f"?restaurant_id={restaurant_id}"
        report_data = requests.get(report_url, headers=headers).json()
    except:
        restaurants = []
        report_data = {"summary": {}, "questions": [], "responses": []}
        
    return render_template("nps_report.html", 
                           restaurants=restaurants, 
                           report=report_data,
                           selected_restaurant=restaurant_id,
                           API_URL=PUBLIC_API_URL)

    # Make sure to pass the auth token to the frontend so it can fetch the ABC report
    return render_template("reporte_restaurantes.html", restaurants=restaurants, API_URL=PUBLIC_API_URL, token=session.get("access_token"))

@app.route("/admin/reports/traffic-intelligence")
def report_traffic_hours():
    if session.get("role") not in ADMIN_ROLES: return redirect(url_for("welcome"))
    headers = get_auth_headers()
    try: restaurants = requests.get(f"{API_URL}/admin/restaurants", headers=headers).json()
    except: restaurants = []
    return render_template("reporte_trafico_horas.html", restaurants=restaurants, API_URL=PUBLIC_API_URL, token=session.get("access_token"))

@app.route("/admin/reports/heatmap-matrix")
def report_heatmap_sales():
    if session.get("role") not in ADMIN_ROLES: return redirect(url_for("welcome"))
    headers = get_auth_headers()
    try: restaurants = requests.get(f"{API_URL}/admin/restaurants", headers=headers).json()
    except: restaurants = []
    return render_template("reporte_heatmap_ventas.html", restaurants=restaurants, API_URL=PUBLIC_API_URL, token=session.get("access_token"))

@app.route("/admin/reports/product-mix")
def report_product_mix():
    if session.get("role") not in ADMIN_ROLES: return redirect(url_for("welcome"))
    headers = get_auth_headers()
    try: restaurants = requests.get(f"{API_URL}/admin/restaurants", headers=headers).json()
    except: restaurants = []
    return render_template("reporte_mix_productos.html", restaurants=restaurants, API_URL=PUBLIC_API_URL, token=session.get("access_token"))

# ── Restaurant ───────────────────────────────────────────────

@app.route("/restaurant/order")
def restaurant_order():
    if session.get("role") != "Restaurant" or session.get("subrole") == "NPS":
        return redirect(url_for("welcome"))
    headers = get_auth_headers()
    selected_date = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    try:
        groups = requests.get(f"{API_URL}/requisitions/product-groups", headers=headers).json()
        products = requests.get(f"{API_URL}/requisitions/products", headers=headers).json()
        res = requests.get(f"{API_URL}/requisitions/active?date={selected_date}", headers=headers)
        today_order = res.json() if res.status_code == 200 else {"status": "None", "items": []}
        report_orders = requests.get(f"{API_URL}/requisitions/report", headers=headers).json()
        eta_days = requests.get(f"{API_URL}/requisitions/eta-days", headers=headers).json().get('eta_days', 2)
    except:
        groups, products, today_order, report_orders, eta_days = [], [], {"status": "None", "items": []}, [], 2

    today_items_map = {item['product_id']: item for item in today_order.get('items', [])}
    return render_template("restaurant_order.html",
                           groups=groups, products=products, today_order=today_order,
                           today_items=today_items_map, report_orders=report_orders,
                           selected_date=selected_date, eta_days=eta_days, API_URL=PUBLIC_API_URL)

@app.route("/restaurant/receiving")
def restaurant_receiving():
    if session.get("role") != "Restaurant" or session.get("subrole") == "NPS":
        return redirect(url_for("welcome"))
    headers = get_auth_headers()
    date_filter = request.args.get("order_date", "")
    try:
        url = f"{API_URL}/requisitions/shipped"
        if date_filter:
            url += f"?order_date={date_filter}"
        orders = requests.get(url, headers=headers).json()
    except:
        orders = []
    return render_template("restaurant_receiving.html", orders=orders, API_URL=PUBLIC_API_URL)

# ── Production Plant ─────────────────────────────────────────

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
        orders = requests.get(url, headers=headers).json()
    except:
        orders = []
    return render_template("production_shipping.html", orders=orders, API_URL=PUBLIC_API_URL)

# ── History ──────────────────────────────────────────────────
@app.route("/history")
@app.route("/history/<int:req_id>")
def history(req_id=None):
    if not session.get("access_token"):
        return redirect(url_for("login"))
    
    if session.get("subrole") == "NPS":
        return redirect(url_for("welcome"))
    headers = get_auth_headers()
    date_filter = request.args.get("order_date", "")
    try:
        role = session.get("role")
        if role == "SuperAdmin":
            url = f"{API_URL}/superadmin/history"
        elif role in ADMIN_ROLES:
            url = f"{API_URL}/admin/history"
        elif role == "Restaurant":
            url = f"{API_URL}/requisitions/history"
        elif role == "Production Plant":
            url = f"{API_URL}/production/history"
        else:
            url = None
        if url:
            if date_filter:
                url += f"?order_date={date_filter}"
            orders = requests.get(url, headers=headers).json()
        else:
            orders = []
    except:
        orders = []
    return render_template("history.html", orders=orders, role=role, API_URL=PUBLIC_API_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
