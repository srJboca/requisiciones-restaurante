from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Numeric, TIMESTAMP, Text, text, Boolean
from sqlalchemy.orm import relationship
from database import Base
from database import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    setting_key = Column(String(50), primary_key=True, index=True)
    setting_value = Column(String(255), nullable=False)

class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    
    users = relationship("User", back_populates="restaurant")
    orders = relationship("Order", back_populates="restaurant")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('Admin', 'Restaurant', 'Production Plant'), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=True)

    restaurant = relationship("Restaurant", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")

class ProductGroup(Base):
    __tablename__ = "product_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)

    products = relationship("Product", back_populates="group")

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), unique=True, nullable=False)
    unit_measure = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    group_id = Column(Integer, ForeignKey("product_groups.id"))

    group = relationship("ProductGroup", back_populates="products")

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    order_date = Column(String(10), nullable=False)  # Storing date as string for simplicity 'YYYY-MM-DD'
    delivery_date = Column(String(10), nullable=True) # ETA date
    status = Column(Enum('Draft', 'Submitted', 'Shipped', 'Closed'), default='Draft', nullable=False)
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
