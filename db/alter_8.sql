-- Add is_urgent column to orders table to support urgent 'Additionals' requisitions
ALTER TABLE requisitions_db.orders ADD COLUMN is_urgent TINYINT(1) DEFAULT 0 NOT NULL AFTER status;
