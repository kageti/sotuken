# dao/product_prices_dao.py
from dataclasses import dataclass
from typing import List, Optional
from contextlib import closing
from db import get_connection

@dataclass
class PricePost:
    price_id: int
    user_id: int
    store_id: Optional[int]
    store_name: str
    jan: str
    product_id: Optional[int]
    product_name: str
    price: int
    posted_at: str

class ProductPricesDAO:
    @staticmethod
    def insert(
        user_id: int,
        store_id: Optional[int],
        store_name: str,
        jan: str,
        product_id: Optional[int],
        product_name: str,
        price: int,
    ) -> int:
        sql = """
            INSERT INTO product_prices
              (user_id, store_id, store_name, jan, product_id, product_name, price)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s)
        """
        conn = get_connection()
        try:
            with closing(conn.cursor()) as cur:
                cur.execute(sql, (user_id, store_id, store_name, jan, product_id, product_name, price))
                conn.commit()
                return cur.lastrowid
        finally:
            conn.close()

    @staticmethod
    def list_recent(limit: int = 10) -> List[PricePost]:
        sql = """
            SELECT
              price_id, user_id, store_id, store_name, jan, product_id, product_name, price,
              DATE_FORMAT(posted_at, '%Y-%m-%d %H:%i:%s') AS posted_at
            FROM product_prices
            ORDER BY posted_at DESC
            LIMIT %s
        """
        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql, (limit,))
                rows = cur.fetchall()
            return [PricePost(**row) for row in rows]
        finally:
            conn.close()
