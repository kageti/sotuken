# dao/store_dao.py

from dataclasses import dataclass
from typing import List, Optional

from db import get_connection


@dataclass
class Store:
    """店舗マスタ 1件分を表すシンプルなモデル"""
    id: int
    name: str
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class StoreDAO:
    """stores テーブルにアクセスする DAO"""

    @staticmethod
    def row_to_store(row) -> Store:
        """
        MySQL の1行（タプル or dict）を Store オブジェクトに変換する。
        db.py の get_connection() の実装によって row の形が違うので、
        必要に応じてここを調整してください。
        """
        # row が dict の場合
        if isinstance(row, dict):
            return Store(
                id=row["id"],
                name=row["name"],
                address=row.get("address"),
                latitude=row.get("latitude"),
                longitude=row.get("longitude"),
            )

        # row がタプルの場合（SELECT 列の順番に注意）
        # 例: SELECT id, name, address, latitude, longitude FROM stores ...
        return Store(
            id=row[0],
            name=row[1],
            address=row[2] if len(row) > 2 else None,
            latitude=row[3] if len(row) > 3 else None,
            longitude=row[4] if len(row) > 4 else None,
        )

    # ------------------------------
    # 1件取得
    # ------------------------------
    @staticmethod
    def find_by_id(store_id: int) -> Optional[Store]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, address, latitude, longitude
                    FROM stores
                    WHERE id = %s
                    """,
                    (store_id,),
                )
                row = cur.fetchone()

        if not row:
            return None
        return StoreDAO.row_to_store(row)

    # ------------------------------
    # 名前で部分一致検索（サジェスト用）
    # ------------------------------
    @staticmethod
    def search_by_name_like(keyword: str, limit: int = 30) -> List[Store]:
        """
        店舗名に keyword が部分一致する店舗を最大 limit 件返す。
        """
        like = f"%{keyword}%"

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, address, latitude, longitude
                    FROM stores
                    WHERE name LIKE %s
                    ORDER BY name
                    LIMIT %s
                    """,
                    (like, limit),
                )
                rows = cur.fetchall()

        return [StoreDAO.row_to_store(row) for row in rows]

    # ------------------------------
    # 新規追加（必要なら）
    # ------------------------------
    @staticmethod
    def insert(name: str,
               address: Optional[str] = None,
               latitude: Optional[float] = None,
               longitude: Optional[float] = None) -> int:
        """
        店舗を1件登録し、採番された id を返す。
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO stores (name, address, latitude, longitude)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (name, address, latitude, longitude),
                )
            conn.commit()
            return cur.lastrowid
