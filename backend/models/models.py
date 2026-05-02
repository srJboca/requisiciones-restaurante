from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Numeric, TIMESTAMP, Text, text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base

# ============================================================
# Company (tenant)
# ============================================================
class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    restaurants = relationship("Restaurant", back_populates="company")
    production_plants = relationship("ProductionPlant", back_populates="company")
    users = relationship("User", back_populates="company")

# ============================================================
# Production Plant (per company)
# ============================================================
class ProductionPlant(Base):
    __tablename__ = "production_plants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    company = relationship("Company", back_populates="production_plants")
    restaurants = relationship("Restaurant", back_populates="production_plant")
    users = relationship("User", back_populates="production_plant", foreign_keys="User.production_plant_id")

# ============================================================
# Restaurant (per company, assigned to a production plant)
# ============================================================
class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    production_plant_id = Column(Integer, ForeignKey("production_plants.id"), nullable=True)

    company = relationship("Company", back_populates="restaurants")
    production_plant = relationship("ProductionPlant", back_populates="restaurants")
    users = relationship("User", back_populates="restaurant", foreign_keys="User.restaurant_id")
    orders = relationship("Order", back_populates="restaurant")

# ============================================================
# User
# SuperAdmin: company_id=NULL, no restaurant/plant
# CompanyAdmin: company_id set, no restaurant/plant
# Restaurant: company_id + restaurant_id set
# Production Plant: company_id + production_plant_id set
# Login: "username@domain" (SuperAdmin: just "superadmin")
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('SuperAdmin', 'CompanyAdmin', 'Restaurant', 'Production Plant'), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)
    production_plant_id = Column(Integer, ForeignKey("production_plants.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint('username', 'company_id', name='uq_username_company'),
    )

    company = relationship("Company", back_populates="users")
    restaurant = relationship("Restaurant", back_populates="users", foreign_keys=[restaurant_id])
    production_plant = relationship("ProductionPlant", back_populates="users", foreign_keys=[production_plant_id])
    audit_logs = relationship("AuditLog", back_populates="user")
    subrole = Column(String(50), default="Requisition", nullable=False)

# ============================================================
# NPS (Net Promoter Score)
# ============================================================
class NPSQuestion(Base):
    __tablename__ = "nps_questions"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    question_text = Column(String(255), nullable=False)
    question_type = Column(Enum('score', 'text', 'yes_no', 'phone', 'email'), default='score')
    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=0)

class NPSSurveyResponse(Base):
    __tablename__ = "nps_survey_responses"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    receipt_ref = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

    restaurant = relationship("Restaurant")
    answers = relationship("NPSSurveyAnswer", back_populates="response")

class NPSSurveyAnswer(Base):
    __tablename__ = "nps_survey_answers"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("nps_survey_responses.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("nps_questions.id"), nullable=False)
    answer_text = Column(Text)

    response = relationship("NPSSurveyResponse", back_populates="answers")
    question = relationship("NPSQuestion")

# ============================================================
# Product Group (per company)
# ============================================================
class ProductGroup(Base):
    __tablename__ = "product_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    company = relationship("Company")
    products = relationship("Product", back_populates="group")

# ============================================================
# Product (per company; SKU unique within a company)
# ============================================================
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), nullable=False)
    unit_measure = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    group_id = Column(Integer, ForeignKey("product_groups.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint('sku', 'company_id', name='uq_sku_company'),
    )

    group = relationship("ProductGroup", back_populates="products")
    company = relationship("Company")

# ============================================================
# System Setting (company_id NULL = global default)
# ============================================================
class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    setting_key = Column(String(50), nullable=False)
    setting_value = Column(String(255), nullable=False)

    __table_args__ = (
        UniqueConstraint('company_id', 'setting_key', name='uq_company_setting'),
    )

# ============================================================
# Order
# ============================================================
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    order_date = Column(String(10), nullable=False)
    delivery_date = Column(String(10), nullable=True)
    status = Column(Enum('Draft', 'Submitted', 'Shipped', 'Closed'), default='Draft', nullable=False)
    
    restaurant_notes = Column(Text, nullable=True)
    production_notes = Column(Text, nullable=True)
    receiving_notes = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
    updated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'))

    submitted_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    shipped_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    received_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    restaurant = relationship("Restaurant", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    shipped_by = relationship("User", foreign_keys=[shipped_by_id])
    received_by = relationship("User", foreign_keys=[received_by_id])

# ============================================================
# Order Item
# ============================================================
class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    current_inventory = Column(Numeric(10, 2), default=0, nullable=False)
    required_quantity = Column(Numeric(10, 2), default=0, nullable=False)
    shipped_quantity = Column(Numeric(10, 2), nullable=True)
    received_quantity = Column(Numeric(10, 2), nullable=True)
    edited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")
    edited_by = relationship("User", foreign_keys=[edited_by_id])

# ============================================================
# Audit Log
# ============================================================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text)
    timestamp = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

    user = relationship("User", back_populates="audit_logs")

# ============================================================
# POS Sale
# ============================================================
class POSSale(Base):
    __tablename__ = "pos_sales"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    order_ref = Column(String(100))
    date_open = Column(String(50))
    date_close = Column(String(50))
    payment_method = Column(String(100))
    product_name = Column(String(255))
    quantity = Column(Numeric(10, 2))
    diners = Column(Integer)
    price_with_tax = Column(Numeric(12, 2))
    total_tip = Column(Numeric(12, 2))
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

    restaurant = relationship("Restaurant")
    company = relationship("Company")

class IgnoredPOSProduct(Base):
    __tablename__ = "ignored_pos_products"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    product_name = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

    company = relationship("Company")

class POSProductMapping(Base):
    __tablename__ = "pos_product_mappings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    product_name = Column(String(255), nullable=False)
    category_name = Column(String(100), default="Uncategorized")
    is_ignored = Column(Boolean, default=False)
    alternative_name = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))

    company = relationship("Company")
