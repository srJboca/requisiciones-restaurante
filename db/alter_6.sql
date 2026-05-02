ALTER TABLE nps_questions MODIFY COLUMN question_type ENUM('score', 'text', 'yes_no', 'phone', 'email') DEFAULT 'score';
