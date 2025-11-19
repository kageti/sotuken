SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS sotuken CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE sotuken;

-- 店舗（将来: 住所/緯度経度もつけられる）
CREATE TABLE IF NOT EXISTS stores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  INDEX idx_store_name (name)
) ENGINE=InnoDB;

-- 商品マスタ
CREATE TABLE IF NOT EXISTS products (
  id INT AUTO_INCREMENT PRIMARY KEY,
  jan VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(255) NOT NULL,
  brand VARCHAR(100) NULL,
  category VARCHAR(100) NULL,
  FULLTEXT KEY ft_name_brand_category (name, brand, category),  -- MySQL 8 の日本語は簡易。LIKEも併用予定
  INDEX idx_jan_prefix (jan)
) ENGINE=InnoDB;

-- 価格テーブル（各店舗ごとの最新価格と信頼値・更新日時を保持）
CREATE TABLE IF NOT EXISTS product_prices (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  product_id INT NOT NULL,
  store_id INT NOT NULL,
  price INT NOT NULL,
  trust INT NOT NULL DEFAULT 50,
  updated_at DATETIME NOT NULL,
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
  FOREIGN KEY (store_id) REFERENCES stores(id) ON DELETE CASCADE,
  INDEX idx_price (price),
  INDEX idx_updated (updated_at),
  INDEX idx_trust (trust),
  UNIQUE KEY uq_product_store (product_id, store_id)  -- 1店舗1商品に1行（最新）
) ENGINE=InnoDB;

-- ユーザー（将来用）
CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
