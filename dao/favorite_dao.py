# dao/favorite_dao.py
import mysql.connector
from db import get_connection

class FavoriteDAO:
    @classmethod
    def toggle(cls, user_id, product_id):
        conn = get_connection()
        cur = conn.cursor(dictionary=True)

        # 既にお気に入り登録済みか確認
        cur.execute("""
            SELECT id FROM favorites
            WHERE user_id=%s AND product_id=%s
        """, (user_id, product_id))
        row = cur.fetchone()

        if row:
            # 削除 → お気に入り解除
            cur.execute("DELETE FROM favorites WHERE id=%s", (row["id"],))
            conn.commit()
            conn.close()
            return False   # 解除後なので False
        else:
            # 新規追加
            cur.execute("""
                INSERT INTO favorites (user_id, product_id, created_at)
                VALUES (%s, %s, NOW())
            """, (user_id, product_id))
            conn.commit()
            conn.close()
            return True    # 登録後なので True

    @classmethod
    def get_favorite_ids(cls, user_id: int):
        """指定ユーザーがお気に入り登録している product_id の集合を返す"""
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT product_id FROM favorites WHERE user_id=%s",
            (user_id,),
        )
        ids = {row[0] for row in cur.fetchall()}
        conn.close()
        return ids
        # dao/favorite_dao.py
from db import get_connection
from contextlib import closing


class FavoriteDAO:
    # --- 既存メソッドはそのまま ---

    @classmethod
    def list_favorites_by_user(cls, user_id: int):
        """
        指定ユーザーのお気に入り商品一覧を返す
        （JANコード・商品名用）
        """
        sql = """
            SELECT
                p.product_id,
                p.jan,
                p.name
            FROM favorites f
            JOIN products p
              ON f.product_id = p.product_id
            WHERE f.user_id = %s
            ORDER BY f.created_at DESC
        """

        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql, (user_id,))
                return cur.fetchall()
        finally:
            conn.close()
