-- ============================================================
-- EMME Tech — SaaS WhatsApp AI Agent Manager
-- Schema v2.0 — MySQL 8+ / MariaDB 10.5+
-- Sistema de créditos + WhatsApp Web + Mercado Pago
-- ============================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- ADMIN
-- ============================================================

CREATE TABLE IF NOT EXISTS `admin_users` (
  `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`          VARCHAR(120) NOT NULL,
  `email`         VARCHAR(180) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role`          ENUM('superadmin','support') NOT NULL DEFAULT 'superadmin',
  `is_active`     TINYINT(1) NOT NULL DEFAULT 1,
  `last_login_at` DATETIME NULL,
  `created_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_admin_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- CONFIGURAÇÕES GLOBAIS (admin configura)
-- ============================================================

CREATE TABLE IF NOT EXISTS `global_settings` (
  `id`          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `key`         VARCHAR(100) NOT NULL,
  `value`       TEXT NULL,
  `description` VARCHAR(255) NULL,
  `updated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_setting_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- PACOTES DE CRÉDITOS
-- ============================================================

CREATE TABLE IF NOT EXISTS `credit_packages` (
  `id`          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`        VARCHAR(80) NOT NULL,
  `credits`     INT UNSIGNED NOT NULL DEFAULT 100,
  `price_brl`   DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  `description` TEXT NULL,
  `is_active`   TINYINT(1) NOT NULL DEFAULT 1,
  `sort_order`  INT NOT NULL DEFAULT 0,
  `created_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TENANTS
-- ============================================================

CREATE TABLE IF NOT EXISTS `tenants` (
  `id`              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`            VARCHAR(150) NOT NULL,
  `slug`            VARCHAR(80) NOT NULL,
  `email`           VARCHAR(180) NOT NULL,
  `status`          ENUM('active','inactive','trial') NOT NULL DEFAULT 'trial',
  `credits`         INT NOT NULL DEFAULT 0,
  `timezone`        VARCHAR(60) NOT NULL DEFAULT 'America/Sao_Paulo',
  `business_name`   VARCHAR(150) NULL,
  `business_phone`  VARCHAR(30) NULL,
  `notes`           TEXT NULL,
  `created_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tenant_slug` (`slug`),
  UNIQUE KEY `uq_tenant_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `tenant_users` (
  `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`     INT UNSIGNED NOT NULL,
  `name`          VARCHAR(120) NOT NULL,
  `email`         VARCHAR(180) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `role`          ENUM('owner','admin','member') NOT NULL DEFAULT 'owner',
  `is_active`     TINYINT(1) NOT NULL DEFAULT 1,
  `last_login_at` DATETIME NULL,
  `created_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tenant_user_email` (`tenant_id`, `email`),
  KEY `fk_tuser_tenant` (`tenant_id`),
  CONSTRAINT `fk_tuser_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- TRANSAÇÕES DE CRÉDITOS
-- ============================================================

CREATE TABLE IF NOT EXISTS `credit_transactions` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`    INT UNSIGNED NOT NULL,
  `amount`       INT NOT NULL COMMENT 'Positivo = adicionado, negativo = consumido',
  `type`         ENUM('bonus','purchase','usage','manual') NOT NULL DEFAULT 'usage',
  `description`  VARCHAR(255) NULL,
  `reference_id` VARCHAR(80) NULL COMMENT 'ID pagamento MP ou mensagem',
  `created_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_ct_tenant` (`tenant_id`),
  KEY `idx_ct_created` (`created_at`),
  CONSTRAINT `fk_ct_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- PAGAMENTOS MERCADO PAGO
-- ============================================================

CREATE TABLE IF NOT EXISTS `mp_payments` (
  `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`     INT UNSIGNED NOT NULL,
  `package_id`    INT UNSIGNED NOT NULL,
  `mp_payment_id` VARCHAR(80) NULL,
  `mp_pref_id`    VARCHAR(120) NULL,
  `amount_brl`    DECIMAL(10,2) NOT NULL,
  `credits`       INT UNSIGNED NOT NULL,
  `status`        ENUM('pending','approved','rejected','cancelled') NOT NULL DEFAULT 'pending',
  `paid_at`       DATETIME NULL,
  `created_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_mp_tenant` (`tenant_id`),
  KEY `idx_mp_payment_id` (`mp_payment_id`),
  CONSTRAINT `fk_mp_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- SESSIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS `sessions` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_type`  ENUM('admin','tenant') NOT NULL,
  `user_id`    INT UNSIGNED NOT NULL,
  `tenant_id`  INT UNSIGNED NULL,
  `token`      CHAR(64) NOT NULL,
  `ip`         VARCHAR(45) NULL,
  `user_agent` VARCHAR(255) NULL,
  `expires_at` DATETIME NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_session_token` (`token`),
  KEY `idx_session_expires` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- MODEL CATALOG (apenas admin configura)
-- ============================================================

CREATE TABLE IF NOT EXISTS `model_catalog` (
  `id`                  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `provider`            VARCHAR(60) NOT NULL DEFAULT 'openrouter',
  `model_id`            VARCHAR(120) NOT NULL,
  `display_name`        VARCHAR(120) NOT NULL,
  `description`         TEXT NULL,
  `context_length`      INT NOT NULL DEFAULT 4096,
  `supports_functions`  TINYINT(1) NOT NULL DEFAULT 0,
  `default_temperature` DECIMAL(3,2) NOT NULL DEFAULT 0.70,
  `default_max_tokens`  INT NOT NULL DEFAULT 1024,
  `is_active`           TINYINT(1) NOT NULL DEFAULT 1,
  `sort_order`          INT NOT NULL DEFAULT 0,
  `created_at`          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_model_id` (`model_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- PERSONAS
-- ============================================================

CREATE TABLE IF NOT EXISTS `personas` (
  `id`           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`    INT UNSIGNED NOT NULL,
  `agent_id`     INT UNSIGNED NULL,
  `name`         VARCHAR(120) NOT NULL,
  `description`  TEXT NULL,
  `instructions` LONGTEXT NULL,
  `tone`         VARCHAR(60) NULL DEFAULT 'professional',
  `language`     VARCHAR(10) NULL DEFAULT 'pt-BR',
  `created_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_persona_tenant` (`tenant_id`),
  CONSTRAINT `fk_persona_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- AGENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS `agents` (
  `id`                               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`                        INT UNSIGNED NOT NULL,
  `name`                             VARCHAR(120) NOT NULL,
  `slug`                             VARCHAR(80) NOT NULL,
  `status`                           ENUM('active','inactive','paused') NOT NULL DEFAULT 'inactive',
  `model_catalog_id`                 INT UNSIGNED NULL,
  `temperature`                      DECIMAL(3,2) NOT NULL DEFAULT 0.70,
  `max_tokens`                       INT NOT NULL DEFAULT 1024,
  `system_prompt`                    LONGTEXT NULL,
  `persona_id`                       INT UNSIGNED NULL,
  -- WhatsApp: modo de conexão
  `whatsapp_mode`                    ENUM('cloud_api','whatsapp_web') NOT NULL DEFAULT 'cloud_api',
  -- Cloud API (Meta)
  `whatsapp_phone_number_id`         VARCHAR(60) NULL,
  `whatsapp_access_token_encrypted`  TEXT NULL,
  `whatsapp_verify_token`            VARCHAR(80) NULL,
  `whatsapp_waba_id`                 VARCHAR(60) NULL,
  -- WhatsApp Web (Evolution API)
  `evo_instance_name`                VARCHAR(80) NULL,
  -- Knowledge Base
  `enable_kb`                        TINYINT(1) NOT NULL DEFAULT 1,
  `kb_top_k`                         INT NOT NULL DEFAULT 3,
  -- Palavras-chave
  `handoff_keyword`                  VARCHAR(80) NULL DEFAULT 'humano',
  `optout_keyword`                   VARCHAR(80) NULL DEFAULT 'sair',
  `created_at`                       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`                       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_agent_tenant_slug` (`tenant_id`, `slug`),
  KEY `fk_agent_tenant` (`tenant_id`),
  KEY `fk_agent_model` (`model_catalog_id`),
  KEY `fk_agent_persona` (`persona_id`),
  CONSTRAINT `fk_agent_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_agent_model` FOREIGN KEY (`model_catalog_id`) REFERENCES `model_catalog` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_agent_persona` FOREIGN KEY (`persona_id`) REFERENCES `personas` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- CONTACTS & THREADS
-- ============================================================

CREATE TABLE IF NOT EXISTS `contacts` (
  `id`               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`        INT UNSIGNED NOT NULL,
  `agent_id`         INT UNSIGNED NOT NULL,
  `phone`            VARCHAR(30) NOT NULL,
  `name`             VARCHAR(120) NULL,
  `opt_out`          TINYINT(1) NOT NULL DEFAULT 0,
  `handoff`          TINYINT(1) NOT NULL DEFAULT 0,
  `last_inbound_at`  DATETIME NULL,
  `metadata`         JSON NULL,
  `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_contact_agent_phone` (`agent_id`, `phone`),
  KEY `fk_contact_tenant` (`tenant_id`),
  KEY `fk_contact_agent` (`agent_id`),
  CONSTRAINT `fk_contact_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_contact_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `threads` (
  `id`               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`        INT UNSIGNED NOT NULL,
  `agent_id`         INT UNSIGNED NOT NULL,
  `contact_id`       INT UNSIGNED NOT NULL,
  `status`           ENUM('open','handoff','closed') NOT NULL DEFAULT 'open',
  `started_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `last_message_at`  DATETIME NULL,
  `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_thread_tenant` (`tenant_id`),
  KEY `fk_thread_agent` (`agent_id`),
  KEY `fk_thread_contact` (`contact_id`),
  KEY `idx_thread_last_msg` (`last_message_at`),
  CONSTRAINT `fk_thread_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_thread_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_thread_contact` FOREIGN KEY (`contact_id`) REFERENCES `contacts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `messages` (
  `id`                  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`           INT UNSIGNED NOT NULL,
  `agent_id`            INT UNSIGNED NOT NULL,
  `thread_id`           INT UNSIGNED NOT NULL,
  `contact_id`          INT UNSIGNED NOT NULL,
  `direction`           ENUM('inbound','outbound') NOT NULL,
  `content`             TEXT NOT NULL,
  `message_type`        VARCHAR(30) NOT NULL DEFAULT 'text',
  `whatsapp_message_id` VARCHAR(120) NULL,
  `dedupe_key`          VARCHAR(120) NULL,
  `status`              ENUM('received','queued','sent','delivered','read','failed') NOT NULL DEFAULT 'received',
  `metadata`            JSON NULL,
  `created_at`          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_dedupe_key` (`dedupe_key`),
  KEY `fk_msg_tenant` (`tenant_id`),
  KEY `fk_msg_agent` (`agent_id`),
  KEY `fk_msg_thread` (`thread_id`),
  KEY `fk_msg_contact` (`contact_id`),
  KEY `idx_msg_created` (`created_at`),
  CONSTRAINT `fk_msg_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_msg_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_msg_thread` FOREIGN KEY (`thread_id`) REFERENCES `threads` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_msg_contact` FOREIGN KEY (`contact_id`) REFERENCES `contacts` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- JOBS QUEUE
-- ============================================================

CREATE TABLE IF NOT EXISTS `jobs` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`    INT UNSIGNED NULL,
  `queue`        VARCHAR(60) NOT NULL DEFAULT 'default',
  `job_class`    VARCHAR(120) NOT NULL,
  `payload`      JSON NOT NULL,
  `status`       ENUM('pending','processing','done','failed') NOT NULL DEFAULT 'pending',
  `attempts`     TINYINT UNSIGNED NOT NULL DEFAULT 0,
  `max_attempts` TINYINT UNSIGNED NOT NULL DEFAULT 3,
  `run_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `started_at`   DATETIME NULL,
  `finished_at`  DATETIME NULL,
  `error`        TEXT NULL,
  `created_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_jobs_status_run_at` (`status`, `run_at`),
  KEY `idx_jobs_queue` (`queue`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- OUTBOX
-- ============================================================

CREATE TABLE IF NOT EXISTS `outbox` (
  `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`        INT UNSIGNED NOT NULL,
  `agent_id`         INT UNSIGNED NOT NULL,
  `contact_id`       INT UNSIGNED NOT NULL,
  `thread_id`        INT UNSIGNED NULL,
  `message_id`       BIGINT UNSIGNED NULL,
  `phone`            VARCHAR(30) NOT NULL,
  `content`          TEXT NOT NULL,
  `message_type`     VARCHAR(30) NOT NULL DEFAULT 'text',
  `template_name`    VARCHAR(80) NULL,
  `template_vars`    JSON NULL,
  `status`           ENUM('pending','sent','failed') NOT NULL DEFAULT 'pending',
  `attempts`         TINYINT UNSIGNED NOT NULL DEFAULT 0,
  `last_attempt_at`  DATETIME NULL,
  `sent_at`          DATETIME NULL,
  `error`            TEXT NULL,
  `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_outbox_status` (`status`),
  KEY `fk_outbox_tenant` (`tenant_id`),
  KEY `fk_outbox_agent` (`agent_id`),
  CONSTRAINT `fk_outbox_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_outbox_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- KNOWLEDGE BASE
-- ============================================================

CREATE TABLE IF NOT EXISTS `kb_docs` (
  `id`            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`     INT UNSIGNED NOT NULL,
  `agent_id`      INT UNSIGNED NOT NULL,
  `filename`      VARCHAR(255) NOT NULL,
  `original_name` VARCHAR(255) NOT NULL,
  `file_type`     VARCHAR(20) NOT NULL DEFAULT 'txt',
  `file_size`     INT UNSIGNED NOT NULL DEFAULT 0,
  `status`        ENUM('pending','processing','ready','error') NOT NULL DEFAULT 'pending',
  `chunk_count`   INT NOT NULL DEFAULT 0,
  `error`         TEXT NULL,
  `created_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_kbdoc_tenant` (`tenant_id`),
  KEY `fk_kbdoc_agent` (`agent_id`),
  CONSTRAINT `fk_kbdoc_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_kbdoc_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `kb_chunks` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`   INT UNSIGNED NOT NULL,
  `agent_id`    INT UNSIGNED NOT NULL,
  `doc_id`      INT UNSIGNED NOT NULL,
  `chunk_index` INT NOT NULL DEFAULT 0,
  `title`       VARCHAR(255) NULL,
  `chunk_text`  MEDIUMTEXT NOT NULL,
  `token_count` INT NOT NULL DEFAULT 0,
  `created_at`  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_chunk_doc` (`doc_id`),
  KEY `idx_chunk_agent` (`agent_id`),
  CONSTRAINT `fk_chunk_doc` FOREIGN KEY (`doc_id`) REFERENCES `kb_docs` (`id`) ON DELETE CASCADE,
  FULLTEXT KEY `ft_chunks` (`title`, `chunk_text`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- CRON JOBS
-- ============================================================

CREATE TABLE IF NOT EXISTS `cron_jobs` (
  `id`               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`        INT UNSIGNED NOT NULL,
  `agent_id`         INT UNSIGNED NOT NULL,
  `name`             VARCHAR(120) NOT NULL,
  `schedule`         VARCHAR(60) NOT NULL DEFAULT '0 9 * * *',
  `is_active`        TINYINT(1) NOT NULL DEFAULT 1,
  `action_type`      ENUM('send_message','send_template','webhook') NOT NULL DEFAULT 'send_template',
  `action_payload`   JSON NULL,
  `template_name`    VARCHAR(80) NULL,
  `template_vars`    JSON NULL,
  `target_type`      ENUM('all_contacts','specific_phone','tag') NOT NULL DEFAULT 'specific_phone',
  `target_value`     VARCHAR(255) NULL,
  `last_run_at`      DATETIME NULL,
  `next_run_at`      DATETIME NULL,
  `created_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_cron_tenant` (`tenant_id`),
  KEY `fk_cron_agent` (`agent_id`),
  KEY `idx_cron_next_run` (`is_active`, `next_run_at`),
  CONSTRAINT `fk_cron_tenant` FOREIGN KEY (`tenant_id`) REFERENCES `tenants` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_cron_agent` FOREIGN KEY (`agent_id`) REFERENCES `agents` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `cron_runs` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `tenant_id`    INT UNSIGNED NOT NULL,
  `cron_job_id`  INT UNSIGNED NOT NULL,
  `status`       ENUM('running','done','failed') NOT NULL DEFAULT 'running',
  `started_at`   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finished_at`  DATETIME NULL,
  `error`        TEXT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_cronrun_job` (`cron_job_id`),
  CONSTRAINT `fk_cronrun_job` FOREIGN KEY (`cron_job_id`) REFERENCES `cron_jobs` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- AUDIT LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS `audit_log` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `actor_type`     ENUM('admin','tenant','system') NOT NULL,
  `actor_id`       INT UNSIGNED NULL,
  `tenant_id`      INT UNSIGNED NULL,
  `action`         VARCHAR(80) NOT NULL,
  `resource_type`  VARCHAR(60) NULL,
  `resource_id`    INT UNSIGNED NULL,
  `old_value`      JSON NULL,
  `new_value`      JSON NULL,
  `ip`             VARCHAR(45) NULL,
  `user_agent`     VARCHAR(255) NULL,
  `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_actor` (`actor_type`, `actor_id`),
  KEY `idx_audit_tenant` (`tenant_id`),
  KEY `idx_audit_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- SEED: Configurações globais padrão
-- ============================================================

INSERT IGNORE INTO `global_settings` (`key`, `value`, `description`) VALUES
('openrouter_api_key', '', 'Chave de API do OpenRouter (global)'),
('openrouter_api_url', 'https://openrouter.ai/api/v1', 'URL base do OpenRouter'),
('mp_access_token', '', 'Mercado Pago — Access Token de produção'),
('mp_public_key', '', 'Mercado Pago — Public Key de produção'),
('mp_webhook_secret', '', 'Mercado Pago — Secret para validar webhooks'),
('evo_api_url', '', 'Evolution API — URL base (ex: https://evo.seudominio.com)'),
('evo_api_key', '', 'Evolution API — Global API Key');

-- ============================================================
-- SEED: Pacotes de créditos padrão
-- ============================================================

INSERT IGNORE INTO `credit_packages` (`name`, `credits`, `price_brl`, `description`, `is_active`, `sort_order`) VALUES
('Inicial',  500,  29.90, '500 respostas do agente', 1, 1),
('Básico',  1000,  49.90, '1.000 respostas do agente', 1, 2),
('Pro',     3000, 129.90, '3.000 respostas do agente', 1, 3),
('Business',10000, 349.90, '10.000 respostas do agente', 1, 4);

-- ============================================================
-- SEED: Model catalog
-- ============================================================

INSERT IGNORE INTO `model_catalog` (`provider`,`model_id`,`display_name`,`description`,`context_length`,`default_temperature`,`default_max_tokens`,`is_active`,`sort_order`) VALUES
('openrouter','openai/gpt-4o-mini','GPT-4o Mini','Rápido e eficiente da OpenAI',128000,0.70,1024,1,1),
('openrouter','openai/gpt-4o','GPT-4o','Mais capaz da OpenAI',128000,0.70,2048,1,2),
('openrouter','anthropic/claude-3-haiku','Claude 3 Haiku','Anthropic — rápido e leve',200000,0.70,1024,1,3),
('openrouter','anthropic/claude-3-sonnet','Claude 3 Sonnet','Anthropic — equilíbrio',200000,0.70,2048,1,4),
('openrouter','meta-llama/llama-3.1-8b-instruct','Llama 3.1 8B','Meta — open source',131072,0.70,1024,1,5),
('openrouter','google/gemini-flash-1.5','Gemini Flash 1.5','Google — rápido',1000000,0.70,1024,1,6);

SET FOREIGN_KEY_CHECKS = 1;
