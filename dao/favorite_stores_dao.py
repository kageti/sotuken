# dao/favorite_stores_dao.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from db import get_connection  

@dataclass
class FavoriteStore:
    """お気に入り店舗 1 件分（favorite_stores テーブル 1行に対応）"""
    user_id: int
    store_id: str
    store_name: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    open_now: Optional[bool] = None
    # 距離表示用（/favorites/stores 側で後からつける）
    distance_km: Optional[float] = None


class FavoriteStoreDAO:
    """
    お気に入り店舗 DAO（DB 版）
    favorite_stores テーブルを操作する
    """

    @classmethod
    def list_by_user(cls, user_id: int) -> List[FavoriteStore]:
        """指定ユーザーのお気に入り店舗一覧を返す"""
        favorites: List[FavoriteStore] = []
        with get_connection() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """
                    SELECT user_id, store_id, store_name,
                           latitude, longitude, open_now
                    FROM favorite_stores
                    WHERE user_id = %s
                    ORDER BY store_name
                    """,
                    (user_id,),
                )
                for row in cur.fetchall():
                    favorites.append(
                        FavoriteStore(
                            user_id=row["user_id"],
                            store_id=row["store_id"],
                            store_name=row["store_name"],
                            latitude=row["latitude"],
                            longitude=row["longitude"],
                            open_now=bool(row["open_now"])
                            if row["open_now"] is not None
                            else None,
                        )
                    )
        return favorites

    @classmethod
    def add(
        cls,
        user_id: int,
        store_id: str,
        store_name: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        open_now: Optional[bool] = None,
    ) -> None:
        """
        お気に入りに追加 or 更新。
        すでに同じ (user_id, store_id) があれば情報を更新する。
        """
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO favorite_stores
                      (user_id, store_id, store_name,
                       latitude, longitude, open_now)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                      store_name = VALUES(store_name),
                      latitude   = VALUES(latitude),
                      longitude  = VALUES(longitude),
                      open_now   = VALUES(open_now)
                    """,
                    (
                        user_id,
                        store_id,
                        store_name,
                        latitude,
                        longitude,
                        1 if open_now is True else 0 if open_now is False else None,
                    ),
                )
            conn.commit()

    @classmethod
    def remove(cls, user_id: int, store_id: str) -> None:
        """お気に入りから削除"""
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM favorite_stores WHERE user_id=%s AND store_id=%s",
                    (user_id, store_id),
                )
            conn.commit()
