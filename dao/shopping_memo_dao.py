# dao/shopping_memo_dao.py
from db import get_connection

class ShoppingMemoDAO:
    @staticmethod
    def add(user_id: int, product_id: int) -> None:
        sql = """
            INSERT IGNORE INTO shopping_memos (user_id, product_id)
            VALUES (%s, %s)
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, product_id))
            conn.commit()

    @staticmethod
    def list_with_products(user_id: int) -> list[dict]:
        sql = """
            SELECT
              sm.product_id,
              p.jan,
              p.name,
              p.brand,
              p.category,
              p.price,
              p.store
            FROM shopping_memos sm
            JOIN products p ON sm.product_id = p.product_id
            WHERE sm.user_id = %s
            ORDER BY sm.created_at DESC
        """
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, (user_id,))
                return cur.fetchall()

    @staticmethod
    def remove(user_id: int, product_id: int) -> None:
        sql = """
            DELETE FROM shopping_memos
            WHERE user_id = %s AND product_id = %s
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (user_id, product_id))
            conn.commit()
