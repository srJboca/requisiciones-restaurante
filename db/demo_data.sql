-- Improved Demo Data for Plateback
USE requisitions_db;

-- 0. Cleanup existing Plateback data to avoid duplicates
-- We do this in a safe order to respect foreign keys
DELETE FROM nps_survey_answers WHERE response_id IN (SELECT id FROM nps_survey_responses WHERE restaurant_id IN (SELECT id FROM restaurants WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co')));
DELETE FROM nps_survey_responses WHERE restaurant_id IN (SELECT id FROM restaurants WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co'));
DELETE FROM nps_questions WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE restaurant_id IN (SELECT id FROM restaurants WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co')));
DELETE FROM orders WHERE restaurant_id IN (SELECT id FROM restaurants WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co'));
DELETE FROM products WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM product_groups WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM pos_product_mappings WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM pos_sales WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM users WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM restaurants WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM production_plants WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM system_settings WHERE company_id IN (SELECT id FROM companies WHERE domain = 'plateback.co');
DELETE FROM companies WHERE domain = 'plateback.co';

-- 1. Create Company
INSERT INTO companies (name, domain) VALUES ('Plateback', 'plateback.co');
SET @company_id = LAST_INSERT_ID();

-- 2. System Settings
INSERT INTO system_settings (company_id, setting_key, setting_value) VALUES 
(@company_id, 'brand_name', 'Plateback'),
(@company_id, 'primary_color', '#3D315B'),
(@company_id, 'nps_thank_you_message', '¡Gracias por visitarnos! Tu opinión es fundamental para nosotros.'),
(@company_id, 'terms_and_conditions_url', 'https://plateback.co/terms'),
(@company_id, 'eta_days', '1');

-- 3. Production Plant
INSERT INTO production_plants (name, company_id) VALUES ('Plateback Central Kitchen', @company_id);
SET @plant_id = LAST_INSERT_ID();

-- 4. Restaurants
INSERT INTO restaurants (name, location, company_id, production_plant_id) VALUES 
('Plateback - North', 'Chico, Bogotá', @company_id, @plant_id),
('Plateback - South', 'Poblado, Medellín', @company_id, @plant_id),
('Plateback - East', 'Zona G, Bogotá', @company_id, @plant_id);

SET @res_north = (SELECT id FROM restaurants WHERE name = 'Plateback - North');
SET @res_south = (SELECT id FROM restaurants WHERE name = 'Plateback - South');
SET @res_east = (SELECT id FROM restaurants WHERE name = 'Plateback - East');

-- 5. Users (admin123 hash)
SET @pass = '$2b$12$RbBuCPCdRQoln.TNTjZpMOPI35HhtH7UIE/Zzo9X7wzoCC6OVqO1q';
INSERT INTO users (username, password_hash, role, company_id) VALUES 
('admin@plateback.co', @pass, 'CompanyAdmin', @company_id);

INSERT INTO users (username, password_hash, role, subrole, company_id, restaurant_id) VALUES 
('north@plateback.co', @pass, 'Restaurant', 'Requisition', @company_id, @res_north),
('south@plateback.co', @pass, 'Restaurant', 'Requisition', @company_id, @res_south),
('survey@plateback.co', @pass, 'Restaurant', 'NPS', @company_id, @res_north);

INSERT INTO users (username, password_hash, role, company_id, production_plant_id) VALUES 
('plant@plateback.co', @pass, 'Production Plant', @company_id, @plant_id);

-- 6. Product Groups
INSERT INTO product_groups (name, company_id) VALUES 
('Abarrotes', @company_id),
('Proteínas', @company_id),
('Lácteos', @company_id),
('Bebidas', @company_id);

SET @group_abarrotes = (SELECT id FROM product_groups WHERE name = 'Abarrotes' AND company_id = @company_id);
SET @group_proteinas = (SELECT id FROM product_groups WHERE name = 'Proteínas' AND company_id = @company_id);
SET @group_lacteos = (SELECT id FROM product_groups WHERE name = 'Lácteos' AND company_id = @company_id);
SET @group_bebidas = (SELECT id FROM product_groups WHERE name = 'Bebidas' AND company_id = @company_id);

-- 7. Products
INSERT INTO products (name, sku, unit_measure, group_id, company_id) VALUES 
('Aceite Vegetal 20L', 'ABA-001', 'Garrafa', @group_abarrotes, @company_id),
('Arroz Blanco 50kg', 'ABA-002', 'Bulto', @group_abarrotes, @company_id),
('Lomo de Res Premium', 'PRO-001', 'Kg', @group_proteinas, @company_id),
('Pechuga de Pollo', 'PRO-002', 'Kg', @group_proteinas, @company_id),
('Leche Entera', 'LAC-001', 'Caja 12L', @group_lacteos, @company_id),
('Queso Mozzarella', 'LAC-002', 'Kg', @group_lacteos, @company_id),
('Agua Mineral 500ml', 'BEB-001', 'Caja 24', @group_bebidas, @company_id);

-- 8. POS Product Mappings (For Analytics)
INSERT INTO pos_product_mappings (company_id, product_name, category_name) VALUES 
(@company_id, 'Burger Classic', 'Main Course'),
(@company_id, 'Burger Deluxe', 'Main Course'),
(@company_id, 'Fries Large', 'Sides'),
(@company_id, 'Coke 350ml', 'Drinks'),
(@company_id, 'Beer Stella', 'Drinks'),
(@company_id, 'Caesar Salad', 'Salads'),
(@company_id, 'Water Still', 'Drinks');

-- 9. POS Sales Data (For Market Basket Analysis)
-- We need multiple items per order_ref
INSERT INTO pos_sales (restaurant_id, company_id, order_ref, date_open, date_close, product_name, quantity, diners, price_with_tax) VALUES 
(@res_north, @company_id, 'T-1001', '2026-05-01 12:00', '2026-05-01 13:00', 'Burger Classic', 1, 1, 25.00),
(@res_north, @company_id, 'T-1001', '2026-05-01 12:00', '2026-05-01 13:00', 'Fries Large', 1, 1, 10.00),
(@res_north, @company_id, 'T-1001', '2026-05-01 12:00', '2026-05-01 13:00', 'Coke 350ml', 1, 1, 5.00),

(@res_north, @company_id, 'T-1002', '2026-05-01 13:30', '2026-05-01 14:30', 'Burger Classic', 2, 2, 50.00),
(@res_north, @company_id, 'T-1002', '2026-05-01 13:30', '2026-05-01 14:30', 'Fries Large', 1, 2, 10.00),

(@res_south, @company_id, 'M-5001', '2026-05-01 19:00', '2026-05-01 20:30', 'Burger Deluxe', 1, 2, 35.00),
(@res_south, @company_id, 'M-5001', '2026-05-01 19:00', '2026-05-01 20:30', 'Beer Stella', 2, 2, 16.00),

(@res_east, @company_id, 'G-7001', '2026-05-02 12:00', '2026-05-02 13:00', 'Caesar Salad', 1, 1, 20.00),
(@res_east, @company_id, 'G-7001', '2026-05-02 12:00', '2026-05-02 13:00', 'Water Still', 1, 1, 4.00);

-- 10. NPS Questions
INSERT INTO nps_questions (company_id, question_text, question_type, display_order) VALUES 
(@company_id, '¿Qué tan probable es que nos recomiendes?', 'score', 0),
(@company_id, '¿Cómo estuvo la comida?', 'text', 1),
(@company_id, '¿El servicio fue rápido?', 'yes_no', 2);

SET @q_score = (SELECT id FROM nps_questions WHERE question_type = 'score' AND company_id = @company_id);
SET @q_text = (SELECT id FROM nps_questions WHERE question_type = 'text' AND company_id = @company_id);

-- 11. NPS Responses
INSERT INTO nps_survey_responses (restaurant_id, receipt_ref) VALUES (@res_north, 'T-1001');
SET @resp_1 = LAST_INSERT_ID();
INSERT INTO nps_survey_answers (response_id, question_id, answer_text) VALUES 
(@resp_1, @q_score, '10'),
(@resp_1, @q_text, 'Excelente servicio y sabor.');

INSERT INTO nps_survey_responses (restaurant_id, receipt_ref) VALUES (@res_south, 'M-5001');
SET @resp_2 = LAST_INSERT_ID();
INSERT INTO nps_survey_answers (response_id, question_id, answer_text) VALUES 
(@resp_2, @q_score, '9'),
(@resp_2, @q_text, 'La hamburguesa estaba un poco salada.');

-- 12. Requisitions (Orders)
INSERT INTO orders (restaurant_id, order_date, delivery_date, status, restaurant_notes) VALUES 
(@res_north, CURDATE(), DATE_ADD(CURDATE(), INTERVAL 1 DAY), 'Submitted', 'Pedido urgente de proteínas.');
SET @order_1 = LAST_INSERT_ID();

INSERT INTO order_items (order_id, product_id, current_inventory, required_quantity) VALUES 
(@order_1, (SELECT id FROM products WHERE sku = 'PRO-001'), 2.5, 10.0),
(@order_1, (SELECT id FROM products WHERE sku = 'PRO-002'), 1.0, 15.0);

INSERT INTO orders (restaurant_id, order_date, delivery_date, status, restaurant_notes, production_notes) VALUES 
(@res_south, DATE_SUB(CURDATE(), INTERVAL 1 DAY), CURDATE(), 'Shipped', 'Reposición semanal.', 'Despachado en camión 1');
SET @order_2 = LAST_INSERT_ID();

INSERT INTO order_items (order_id, product_id, current_inventory, required_quantity, shipped_quantity) VALUES 
(@order_2, (SELECT id FROM products WHERE sku = 'ABA-001'), 0, 2.0, 2.0),
(@order_2, (SELECT id FROM products WHERE sku = 'LAC-001'), 5.0, 10.0, 10.0);
