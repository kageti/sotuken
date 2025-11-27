# dao/product_price_dao.py
from typing import List, Optional
from db import get_connection

class ProductPriceWithName:
    """JOIN した結果をまとめる用"""
    def __init__(
        self,
        price_id: int,
        price: int,
        trust: int,
        updated_at,
        product_name: str,
        store_name: str
    ):
        self.price_id = price_id
        self.price = price
        self.trust = trust
        self.updated_at = updated_at
        self.product_name = product_name
        self.store_name = store_name

class ProductPriceDAO:

    @staticmethod
    def find_by_product_id(product_id: int) -> List[ProductPriceWithName]:
        sql = """
            SELECT
              pp.id       AS price_id,
              pp.price,
              pp.trust,
              pp.updated_at,
              p.name      AS product_name,
              s.name      AS store_name
            FROM product_prices pp
              JOIN products p ON pp.product_id = p.id
              JOIN stores   s ON pp.store_id   = s.id
            WHERE pp.product_id = %s
            ORDER BY pp.price ASC
        """
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, (product_id,))
                rows = cur.fetchall()
            return [ProductPriceWithName(**row) for row in rows]
        finally:
            conn.close()
