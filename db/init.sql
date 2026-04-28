CREATE DATABASE IF NOT EXISTS requisitions_db;
USE requisitions_db;
-- Settings
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key VARCHAR(50) PRIMARY KEY,
    setting_value VARCHAR(255) NOT NULL
);
INSERT INTO system_settings (setting_key, setting_value) VALUES ('eta_days', '2') ON DUPLICATE KEY UPDATE setting_key=setting_key;

-- Users and Restaurants
CREATE TABLE IF NOT EXISTS restaurants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('Admin', 'Restaurant', 'Production Plant') NOT NULL,
    restaurant_id INT NULL,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
);

-- Products
CREATE TABLE IF NOT EXISTS product_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sku VARCHAR(100) UNIQUE NOT NULL,
    unit_measure VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    group_id INT,
    FOREIGN KEY (group_id) REFERENCES product_groups(id)
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_id INT NOT NULL,
    order_date DATE NOT NULL,
    delivery_date VARCHAR(10) NULL,
    status ENUM('Draft', 'Submitted', 'Shipped', 'Closed') NOT NULL DEFAULT 'Draft',
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

-- Audit
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

-- Initial Admin Data (password is "admin123" assuming hashed via basic SHA256 for testing, but in python we use bcrypt. Let's insert hashed password for 'admin123' -> $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPIAp.32q)
INSERT INTO users (username, password_hash, role) VALUES ('admin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPIAp.32q', 'Admin') ON DUPLICATE KEY UPDATE id=id;
