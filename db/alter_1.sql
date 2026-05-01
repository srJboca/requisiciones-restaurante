CREATE TABLE IF NOT EXISTS requisitions_db.pos_sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_id INT NOT NULL,
    company_id INT NOT NULL,
    order_ref VARCHAR(100),
    date_open VARCHAR(50),
    date_close VARCHAR(50),
    payment_method VARCHAR(100),
    product_name VARCHAR(255),
    quantity DECIMAL(10, 2),
    diners INT,
    price_with_tax DECIMAL(12, 2),
    total_tip DECIMAL(12, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
