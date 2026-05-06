ALTER TABLE users MODIFY COLUMN role ENUM('SuperAdmin', 'CompanyAdmin', 'Restaurant', 'Production Plant', 'Business User') NOT NULL;
