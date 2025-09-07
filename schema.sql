CREATE DATABASE IF NOT EXISTS finflow_db;
USE finflow_db;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  first_name VARCHAR(50),
  last_name VARCHAR(50),
  email VARCHAR(100) UNIQUE,
  password VARCHAR(255),
  occupation VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  description VARCHAR(255),
  amount DECIMAL(12,2) NOT NULL DEFAULT 0,
  category ENUM('Income','Expense') NOT NULL,
  subcategory VARCHAR(100),
  transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_date (user_id, transaction_date),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Optional table to store generated insights/advice (not required to run)
CREATE TABLE IF NOT EXISTS ai_insights (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  kind VARCHAR(50),          -- 'advice' | 'insight' | 'alert'
  message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
