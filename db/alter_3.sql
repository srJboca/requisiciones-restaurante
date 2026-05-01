CREATE TABLE IF NOT EXISTS requisitions_db.pos_product_mappings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category_name VARCHAR(100) DEFAULT 'Uncategorized',
    is_ignored BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_company_product_mapping (company_id, product_name),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
