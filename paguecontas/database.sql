-- PagueContas Database Schema
CREATE DATABASE IF NOT EXISTS paguecontas_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE paguecontas_db;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    cpf VARCHAR(14) DEFAULT NULL,
    phone VARCHAR(20) DEFAULT NULL,
    balance DECIMAL(12,2) DEFAULT 0.00,
    cashback_balance DECIMAL(12,2) DEFAULT 0.00,
    is_admin TINYINT(1) DEFAULT 0,
    status ENUM('active', 'inactive', 'blocked') DEFAULT 'active',
    avatar VARCHAR(255) DEFAULT NULL,
    email_verified_at DATETIME DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Transactions table
CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type ENUM('deposit', 'payment', 'cashback', 'cashback_used', 'refund') NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    balance_after DECIMAL(12,2) NOT NULL,
    description VARCHAR(255) NOT NULL,
    barcode VARCHAR(100) DEFAULT NULL,
    bill_type ENUM('boleto', 'energia', 'agua', 'gas', 'telefone', 'internet', 'outro') DEFAULT NULL,
    cashback_amount DECIMAL(12,2) DEFAULT 0.00,
    status ENUM('pending', 'completed', 'failed', 'cancelled') DEFAULT 'pending',
    reference_id VARCHAR(50) DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Recharges table
CREATE TABLE IF NOT EXISTS recharges (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    payment_method ENUM('pix', 'credit_card', 'bank_transfer') NOT NULL,
    status ENUM('pending', 'approved', 'rejected', 'cancelled') DEFAULT 'pending',
    proof_file VARCHAR(255) DEFAULT NULL,
    approved_by INT DEFAULT NULL,
    approved_at DATETIME DEFAULT NULL,
    reference_code VARCHAR(50) NOT NULL,
    notes TEXT DEFAULT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Admin activity log
CREATE TABLE IF NOT EXISTS admin_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    admin_id INT NOT NULL,
    action VARCHAR(100) NOT NULL,
    description TEXT,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- System settings
CREATE TABLE IF NOT EXISTS settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Notifications
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    type ENUM('info', 'success', 'warning', 'danger') DEFAULT 'info',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Foreign Keys
ALTER TABLE transactions ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE recharges ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE recharges ADD FOREIGN KEY (approved_by) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE admin_logs ADD FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE notifications ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Indexes
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_type ON transactions(type);
CREATE INDEX idx_transactions_created ON transactions(created_at);
CREATE INDEX idx_recharges_user ON recharges(user_id);
CREATE INDEX idx_recharges_status ON recharges(status);
CREATE INDEX idx_notifications_user ON notifications(user_id);

-- Default admin user (password: admin123)
INSERT INTO users (name, email, password, is_admin, status, email_verified_at) VALUES
('Administrador', 'admin@paguecontas.com', '$2y$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 1, 'active', NOW());

-- Default settings
INSERT INTO settings (setting_key, setting_value) VALUES
('cashback_percent', '5'),
('min_deposit', '10.00'),
('max_deposit', '10000.00'),
('min_payment', '5.00'),
('max_payment', '50000.00'),
('pix_key', 'paguecontas@pix.com'),
('maintenance_mode', '0'),
('site_name', 'PagueContas'),
('site_description', 'Pague suas contas e ganhe cashback de volta!');
