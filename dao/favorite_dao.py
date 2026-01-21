# dao/favorite_dao.py
from __future__ import annotations

from typing import List, Dict, Set, Optional
from contextlib import closing

from db import get_connection


class FavoriteDAO:
    @classmethod
    def toggle(cls, user_id: int, product_id: int) -> bool:
        """
        favorites に (user_id, product_id) があれば削除、なければ追加。
        戻り値: True=登録後, False=解除後
        """
        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(
                    """
                    SELECT id FROM favorites
                    WHERE user_id=%s AND product_id=%s
                    """,
                    (user_id, product_id),
                )
                row = cur.fetchone()

                if row:
                    cur.execute("DELETE FROM favorites WHERE id=%s", (row["id"],))
                    conn.commit()
                    return False
                else:
                    cur.execute(
                        """
                        INSERT INTO favorites (user_id, product_id, created_at)
                        VALUES (%s, %s, NOW())
                        """,
                        (user_id, product_id),
                    )
                    conn.commit()
                    return True
        finally:
            conn.close()

    @classmethod
    def get_favorite_ids(cls, user_id: int) -> Set[int]:
        """指定ユーザーがお気に入り登録している product_id の集合を返す"""
        conn = get_connection()
        try:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    "SELECT product_id FROM favorites WHERE user_id=%s",
                    (user_id,),
                )
                return {row[0] for row in cur.fetchall()}
        finally:
            conn.close()

    @classmethod
    def remove(cls, user_id: int, product_id: int) -> None:
        """明示的にお気に入り解除"""
        conn = get_connection()
        try:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    "DELETE FROM favorites WHERE user_id=%s AND product_id=%s",
                    (user_id, product_id),
                )
            conn.commit()
        finally:
            conn.close()

    @classmethod
    def list_favorites_by_user(cls, user_id: int) -> List[Dict]:
        """
        お気に入り商品一覧用（JAN と商品名を表示する想定）
        products テーブルと JOIN して返す
        """
        sql = """
            SELECT
              f.product_id,
              p.jan,
              p.name
            FROM favorites f
            JOIN products p ON p.product_id = f.product_id
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
