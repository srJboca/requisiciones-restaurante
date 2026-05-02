-- NPS System Migration
-- 1. Add subrole to users
ALTER TABLE requisitions_db.users ADD COLUMN subrole VARCHAR(50);

-- 2. NPS Questions
CREATE TABLE requisitions_db.nps_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    company_id INT NOT NULL,
    question_text VARCHAR(255) NOT NULL,
    question_type ENUM('score', 'text', 'yes_no') DEFAULT 'score',
    is_active BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 0,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- 3. NPS Survey Responses
CREATE TABLE requisitions_db.nps_survey_responses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    restaurant_id INT NOT NULL,
    receipt_ref VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (restaurant_id) REFERENCES restaurants(id)
);

-- 4. NPS Survey Answers
CREATE TABLE requisitions_db.nps_survey_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    response_id INT NOT NULL,
    question_id INT NOT NULL,
    answer_text TEXT,
    FOREIGN KEY (response_id) REFERENCES nps_survey_responses(id),
    FOREIGN KEY (question_id) REFERENCES nps_questions(id)
);
