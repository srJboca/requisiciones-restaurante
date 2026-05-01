-- Add alternative_name to pos_product_mappings
ALTER TABLE pos_product_mappings ADD COLUMN alternative_name VARCHAR(255) NULL;
