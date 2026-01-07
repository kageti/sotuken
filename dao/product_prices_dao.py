# dao/product_prices_dao.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Any, Dict
from contextlib import closing

from db import get_connection


@dataclass
class PricePost:
    """
    product_prices テーブル1行分を表すクラス
    """
    price_id: int
    user_id: int
    store_id: Optional[int]
    store_name: str
    jan: str
    product_id: Optional[int]
    product_name: str
    price: int
    posted_at: str  # 画面表示しやすいように文字列にしています（DATE_FORMATの結果）


class ProductPricesDAO:
    """
    product_prices テーブル用 DAO
    """

    @staticmethod
    def add_post(
        *,
        user_id: int,
        store_id: Optional[int],
        store_name: str,
        jan: str,
        product_id: Optional[int],
        product_name: str,
        price: int,
    ) -> int:
        """
        価格投稿をDBへ保存し、作成された price_id を返す
        """
        sql = """
            INSERT INTO product_prices
              (user_id, store_id, store_name, jan, product_id, product_name, price, posted_at)
            VALUES
              (%s, %s, %s, %s, %s, %s, %s, NOW())
        """

        conn = get_connection()
        try:
            with closing(conn.cursor()) as cur:
                cur.execute(
                    sql,
                    (
                        user_id,
                        store_id,
                        store_name,
                        jan,
                        product_id,
                        product_name,
                        price,
                    ),
                )
                conn.commit()
                return int(cur.lastrowid)
        finally:
            conn.close()

    @staticmethod
    def list_recent(limit: int = 10) -> List[PricePost]:
        """
        最新の投稿を新しい順で取得
        ※ LIMIT はプレースホルダにせず、int化してSQLに埋め込み（connector対策）
        """
        limit = int(limit)

        sql = f"""
            SELECT
              price_id,
              user_id,
              store_id,
              store_name,
              jan,
              product_id,
              product_name,
              price,
              DATE_FORMAT(posted_at, '%Y-%m-%d %H:%i:%s') AS posted_at
            FROM product_prices
            ORDER BY posted_at DESC
            LIMIT {limit}
        """

        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql)
                rows = cur.fetchall() or []
            return [ProductPricesDAO._row_to_pricepost(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def list_by_user(user_id: int, limit: int = 50) -> List[PricePost]:
        """
        ユーザー別の投稿一覧（新しい順）
        """
        limit = int(limit)

        sql = f"""
            SELECT
              price_id,
              user_id,
              store_id,
              store_name,
              jan,
              product_id,
              product_name,
              price,
              DATE_FORMAT(posted_at, '%Y-%m-%d %H:%i:%s') AS posted_at
            FROM product_prices
            WHERE user_id = %s
            ORDER BY posted_at DESC
            LIMIT {limit}
        """

        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql, (user_id,))
                rows = cur.fetchall() or []
            return [ProductPricesDAO._row_to_pricepost(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def list_by_store(store_id: int, limit: int = 50) -> List[PricePost]:
        """
        店舗別の投稿一覧（新しい順）
        """
        limit = int(limit)

        sql = f"""
            SELECT
              price_id,
              user_id,
              store_id,
              store_name,
              jan,
              product_id,
              product_name,
              price,
              DATE_FORMAT(posted_at, '%Y-%m-%d %H:%i:%s') AS posted_at
            FROM product_prices
            WHERE store_id = %s
            ORDER BY posted_at DESC
            LIMIT {limit}
        """

        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql, (store_id,))
                rows = cur.fetchall() or []
            return [ProductPricesDAO._row_to_pricepost(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def list_by_jan(jan: str, limit: int = 50) -> List[PricePost]:
        """
        JAN別の投稿一覧（新しい順）
        """
        limit = int(limit)

        sql = f"""
            SELECT
              price_id,
              user_id,
              store_id,
              store_name,
              jan,
              product_id,
              product_name,
              price,
              DATE_FORMAT(posted_at, '%Y-%m-%d %H:%i:%s') AS posted_at
            FROM product_prices
            WHERE jan = %s
            ORDER BY posted_at DESC
            LIMIT {limit}
        """

        conn = get_connection()
        try:
            with closing(conn.cursor(dictionary=True)) as cur:
                cur.execute(sql, (jan,))
                rows = cur.fetchall() or []
            return [ProductPricesDAO._row_to_pricepost(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def delete_post(price_id: int, user_id: int) -> bool:
        """
        投稿削除（本人のみ削除できる想定）
        """
        sql = """
            DELETE FROM product_prices
            WHERE price_id = %s AND user_id = %s
        """

        conn = get_connection()
        try:
            with closing(conn.cursor()) as cur:
                cur.execute(sql, (price_id, user_id))
                conn.commit()
                return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def _row_to_pricepost(row: Dict[str, Any]) -> PricePost:
        """
        dictionary=True の行を PricePost に変換
        """
        # row のキーがSQLと一致している前提
        return PricePost(
            price_id=int(row["price_id"]),
            user_id=int(row["user_id"]),
            store_id=(int(row["store_id"]) if row.get("store_id") is not None else None),
            store_name=str(row.get("store_name") or ""),
            jan=str(row.get("jan") or ""),
            product_id=(int(row["product_id"]) if row.get("product_id") is not None else None),
            product_name=str(row.get("product_name") or ""),
            price=int(row.get("price") or 0),
            posted_at=str(row.get("posted_at") or ""),
        )
