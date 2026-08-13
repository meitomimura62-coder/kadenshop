USE app;
SET NAMES utf8mb4;

DROP TABLE IF EXISTS cart;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;

CREATE TABLE products (
  product_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  description TEXT NULL,
  price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  stock INT UNSIGNED NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (product_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE users (
  user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'member',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cart (
  cart_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id BIGINT UNSIGNED NOT NULL,
  quantity INT UNSIGNED NOT NULL DEFAULT 1,
  added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (cart_id),
  UNIQUE KEY uq_cart_product (product_id),
  CONSTRAINT fk_cart_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE orders (
  order_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  customer_name VARCHAR(255) NOT NULL DEFAULT 'ゲスト',
  user_id BIGINT UNSIGNED NULL,
  total_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
  status VARCHAR(32) NOT NULL DEFAULT 'confirmed',
  details JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (order_id),
  KEY idx_orders_user_created (user_id, created_at),
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO products (name, description, price, stock) VALUES
  ('4Kスマートテレビ 55インチ', 'HDR対応で映像が美しい55インチ4Kスマートテレビ。各種動画サービスも内蔵しています。', 79800.00, 5),
  ('ノイズキャンセリングワイヤレスイヤホン', '長時間再生対応の完全ワイヤレスイヤホン。通勤や運動時にも便利です。', 12980.00, 12),
  ('防水ポータブルBluetoothスピーカー', 'アウトドアでも使える防水仕様。クリアなサウンドをどこでも楽しめます。', 6980.00, 10),
  ('スマート電子レンジ 700W', '簡単操作のタッチパネル電子レンジ。自動メニュー搭載で使いやすいです。', 14980.00, 7);

INSERT INTO products (name, description, price, stock) VALUES
  ('ゲーミングモニター 27インチ', '144Hz IPSパネル', 42800.00, 8);

INSERT INTO products (name, description, price, stock) VALUES
  ('ロボット掃除機 X100','スマートマッピング対応のロボット掃除機',39800.00,15),
  ('スマート冷蔵庫 300L','省エネ設計で庫内を見える化できるスマート冷蔵庫',129800.00,3),
  ('4Kプロジェクター','家庭用の高輝度4Kプロジェクター',99800.00,4),
  ('ミラーレス一眼カメラ 24MP','コンパクトで高画質なミラーレスカメラ',89900.00,6),
  ('ポータブル電源 500Wh','キャンプや非常用に使えるポータブル電源',39800.00,10),
  ('スマートウォッチ Pro','心拍・睡眠トラッキング対応スマートウォッチ',19800.00,20),
  ('外付けSSD 1TB','高速USB-C接続のポータブルSSD',14980.00,25),
  ('ゲーム機 据え置き','最新世代の据え置きゲームコンソール',54980.00,8),
  ('ワイヤレスキーボード＆マウスセット','薄型ワイヤレスキーボードとマウスのセット',5980.00,30),
  ('電動歯ブラシ プレミアム','高振動で歯垢除去に優れる電動歯ブラシ',8980.00,18);

CREATE TABLE questions (
  question_id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  exam_name      VARCHAR(255) NOT NULL DEFAULT '基本情報技術者試験',
  domain_name    VARCHAR(64)  NOT NULL,
  topic_name     VARCHAR(64)  NULL,
  title          VARCHAR(255) NULL,
  stem           TEXT NOT NULL,
  explanation    MEDIUMTEXT NULL,
  correct_label  CHAR(1) NOT NULL,
  difficulty     TINYINT UNSIGNED NULL,
  is_active      TINYINT(1) NOT NULL DEFAULT 1,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (question_id),
  KEY idx_q_domain (domain_name),
  KEY idx_q_topic (topic_name),
  KEY idx_q_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE question_choices (
  choice_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  question_id   BIGINT UNSIGNED NOT NULL,
  choice_label  CHAR(1) NOT NULL,
  choice_text   TEXT NOT NULL,
  PRIMARY KEY (choice_id),
  UNIQUE KEY uk_q_label (question_id, choice_label),
  KEY idx_choice_q (question_id),
  CONSTRAINT fk_choice_q
    FOREIGN KEY (question_id) REFERENCES questions(question_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE answers (
  answer_id       BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id         BIGINT UNSIGNED NOT NULL,
  question_id     BIGINT UNSIGNED NOT NULL,
  selected_label  CHAR(1) NOT NULL,
  is_correct      TINYINT(1) NOT NULL,
  elapsed_ms      INT UNSIGNED NULL,
  answered_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (answer_id),
  KEY idx_ans_user_time (user_id, answered_at),
  KEY idx_ans_q_time (question_id, answered_at),
  KEY idx_ans_correct (question_id, is_correct),
  CONSTRAINT fk_ans_q
    FOREIGN KEY (question_id) REFERENCES questions(question_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
