CREATE TABLE IF NOT EXISTS requisitions_db.ignored_pos_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_company_product (company_id, product_name),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);