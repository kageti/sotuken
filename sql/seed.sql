SET NAMES utf8mb4;

USE sotuken;

INSERT INTO stores (name) VALUES
('スーパーA 広島駅前店'),
('ドラッグB 猿猴橋店'),
('スーパーC 段原店'),
('スーパーD 横川店'),
('コンビニE 広大病院前店');

INSERT INTO products (jan, name, brand, category) VALUES
('4901234567890','明治 おいしい牛乳 1000ml','明治','乳製品'),
('4902713123456','日清 カップヌードル しょうゆ 78g','日清','インスタント'),
('4901777301234','コカ・コーラ 500ml ペット','コカ・コーラ','飲料'),
('4901002134567','キッコーマン しょうゆ 1L','キッコーマン','調味料'),
('4901085198765','ハウス バーモントカレー 中辛 230g','ハウス','レトルト'),
('4901411234001','サントリー 天然水 2L','サントリー','飲料'),
('4903301234567','ヤマザキ ダブルソフト 6枚','山崎製パン','パン'),
('4902720123012','UCC ブラック無糖 185g 缶','UCC','飲料');
('4901919454519','JA コシヒカリ 5kg','JA','米');

-- 店舗名→ID を使って価格データ投入
-- 便宜上、NOW() で更新時刻を入れています
INSERT INTO product_prices (product_id, store_id, price, trust, updated_at) VALUES
-- 牛乳
((SELECT id FROM products WHERE jan='4901234567890'), (SELECT id FROM stores WHERE name='スーパーA 広島駅前店'), 228,72, NOW() - INTERVAL 7 DAY),
-- カップヌードル
((SELECT id FROM products WHERE jan='4902713123456'), (SELECT id FROM stores WHERE name='ドラッグB 猿猴橋店'), 158,65, NOW() - INTERVAL 1 DAY),
-- コーラ
((SELECT id FROM products WHERE jan='4901777301234'), (SELECT id FROM stores WHERE name='スーパーA 広島駅前店'), 98,80, NOW() - INTERVAL 6 DAY),
-- しょうゆ
((SELECT id FROM products WHERE jan='4901002134567'), (SELECT id FROM stores WHERE name='スーパーC 段原店'), 268,55, NOW() - INTERVAL 2 DAY),
-- バーモント
((SELECT id FROM products WHERE jan='4901085198765'), (SELECT id FROM stores WHERE name='ドラッグB 猿猴橋店'), 198,60, NOW() - INTERVAL 3 DAY),
-- 天然水
((SELECT id FROM products WHERE jan='4901411234001'), (SELECT id FROM stores WHERE name='スーパーD 横川店'), 95,77, NOW()),
-- ダブルソフト
((SELECT id FROM products WHERE jan='4903301234567'), (SELECT id FROM stores WHERE name='スーパーC 段原店'), 178,58, NOW() - INTERVAL 5 DAY),
-- UCC 缶
((SELECT id FROM products WHERE jan='4902720123012'), (SELECT id FROM stores WHERE name='コンビニE 広大病院前店'), 78,68, NOW() - INTERVAL 4 DAY);
-- 米
((SELECT id FROM products WHERE jan='4901919454519'), (SELECT id FROM stores WHERE name='スーパーC 段原店'), 4,980,68, NOW() - INTERVAL 4 DAY);
