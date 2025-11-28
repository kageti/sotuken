# dao/products_dao.py
from typing import List, Optional
from datetime import datetime
from contextlib import closing   # ★ 追加
from db import get_connection


class Product:
    """products テーブル1行分を表すクラス"""

    def __init__(
        self,
        id: int,
        jan: str,
        name: str,
        brand: str,
        category: str,
        price: int,
        store: str,
        trust: int,
        updated_at: datetime,
    ):
        self.id = id
        self.jan = jan
        self.name = name
        self.brand = brand
        self.category = category
        self.price = price
        self.store = store
        self.trust = trust
        self.updated_at = updated_at


class ProductDAO:
    """products テーブル用 DAO"""

    @staticmethod
    def search_by_keyword(keyword: str) -> List[Product]:
        """
        フリーワード検索（名前・ブランド・カテゴリ・店舗名・JAN）
        """
        sql = """
            SELECT
                product_id AS id,
                jan,
                name,
                brand,
                category,
                price,
                store,
                trust,
                updated_at
            FROM products
            WHERE name     LIKE %s
               OR brand    LIKE %s
               OR category LIKE %s
               OR store    LIKE %s
               OR jan      LIKE %s
        """
        like = f"%{keyword}%"
        conn = get_connection()
        try:
            # ★ ここを closing(...) に変更
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql, (like, like, like, like, like))
                rows = cur.fetchall()
            return [Product(**row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def find_by_id(product_id: int) -> Optional[Product]:
        sql = """
            SELECT
                product_id AS id,
                jan,
                name,
                brand,
                category,
                price,
                store,
                trust,
                updated_at
            FROM products
            WHERE product_id = %s
        """
        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql, (product_id,))
                row = cur.fetchone()
            if row is None:
                return None
            return Product(**row)
        finally:
            conn.close()

    @staticmethod
    def find_by_jan(jan: str) -> Optional[Product]:
        sql = """
            SELECT
                product_id AS id,
                jan,
                name,
                brand,
                category,
                price,
                store,
                trust,
                updated_at
            FROM products
            WHERE jan = %s
        """
        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql, (jan,))
                row = cur.fetchone()
            if row is None:
                return None
            return Product(**row)
        finally:
            conn.close()
