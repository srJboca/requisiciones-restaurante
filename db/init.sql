CREATE DATABASE IF NOT EXISTS requisitions_db;
USE requisitions_db;

-- ============================================================
-- Companies (tenants)
-- ============================================================
CREATE TABLE IF NOT EXISTS companies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(100) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

-- ============================================================
-- Production Plants (per company)
-- ============================================================
CREATE TABLE IF NOT EXISTS production_plants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    company_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- Restaurants (per company, optionally assigned to a plant)
-- ============================================================
CREATE TABLE IF NOT EXISTS restaurants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    company_id INT NOT NULL,
    production_plant_id INT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (production_plant_id) REFERENCES production_plants(id)
);

-- ============================================================
-- Users  (SuperAdmin has company_id = NULL)
-- Login format: "username@domain"  (SuperAdmin: just "superadmin")
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('SuperAdmin', 'CompanyAdmin', 'Restaurant', 'Production Plant') NOT NULL,
    company_id INT NULL,
    restaurant_id INT NULL,
    production_plant_id INT NULL,
    UNIQUE KEY uq_username_company (username, company_id),
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
    FOREIGN KEY (production_plant_id) REFERENCES production_plants(id)
);

-- ============================================================
-- Product Groups and Products (per company)
-- ============================================================
CREATE TABLE IF NOT EXISTS product_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    company_id INT NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    unit_measure VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    group_id INT NULL,
    company_id INT NOT NULL,
    UNIQUE KEY uq_sku_company (sku, company_id),
    FOREIGN KEY (group_id) REFERENCES product_groups(id),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ============================================================
-- System Settings (company_id NULL = global default)
-- ============================================================
CREATE TABLE IF NOT EXISTS system_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NULL,
    setting_key VARCHAR(50) NOT NULL,
    setting_value VARCHAR(255) NOT NULL,
    UNIQUE KEY uq_company_setting (company_id, setting_key),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- Global defaults
INSERT INTO system_settings (company_id, setting_key, setting_value) VALUES (NULL, 'eta_days', '2')
  ON DUPLICATE KEY UPDATE setting_value=setting_value;
INSERT INTO system_settings (company_id, setting_key, setting_value) VALUES (NULL, 'default_language', 'en')
  ON DUPLICATE KEY UPDATE setting_value=setting_value;

-- ============================================================
-- Orders and Order Items
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_id INT NOT NULL,
    order_date DATE NOT NULL,
    delivery_date VARCHAR(10) NULL,
    status ENUM('Draft', 'Submitted', 'Shipped', 'Closed') NOT NULL DEFAULT 'Draft',
    restaurant_notes TEXT NULL,
    production_notes TEXT NULL,
    receiving_notes TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    submitted_by_id INT NULL,
    shipped_by_id INT NULL,
    received_by_id INT NULL,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id),
    FOREIGN KEY (submitted_by_id) REFERENCES users(id),
    FOREIGN KEY (shipped_by_id) REFERENCES users(id),
    FOREIGN KEY (received_by_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS order_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    current_inventory DECIMAL(10,2) NOT NULL DEFAULT 0,
    required_quantity DECIMAL(10,2) NOT NULL DEFAULT 0,
    shipped_quantity DECIMAL(10,2) NULL,
    received_quantity DECIMAL(10,2) NULL,
    edited_by_id INT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (edited_by_id) REFERENCES users(id)
);

-- ============================================================
-- Audit Log
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(255) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id INT NULL,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- ============================================================
-- Seed Data
-- password hash = bcrypt("admin123")
-- ============================================================
-- SuperAdmin (platform-wide, no company)
INSERT INTO users (username, password_hash, role, company_id)
VALUES ('superadmin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPIAp.32q', 'SuperAdmin', NULL)
ON DUPLICATE KEY UPDATE id=id;

-- Sample company: La Cesta
INSERT INTO companies (name, domain, is_active) VALUES ('La Cesta', 'lacesta', TRUE)
ON DUPLICATE KEY UPDATE id=id;

-- CompanyAdmin for La Cesta  (login: admin@lacesta / admin123)
INSERT INTO users (username, password_hash, role, company_id)
SELECT 'admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPIAp.32q', 'CompanyAdmin', c.id
FROM companies c WHERE c.domain='lacesta'
ON DUPLICATE KEY UPDATE username=username;
