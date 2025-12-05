# dao/favorite_stores_dao.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class FavoriteStore:
    """お気に入り店舗 1 件分を表すクラス（将来 DB の行に対応）"""
    user_id: int          # users.id（INT 外部キー想定）
    store_id: str         # stores.id 相当（文字列 or 数値文字列）
    store_name: str       # 店舗名（stores.name）
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    open_now: Optional[bool] = None  # True: 営業中, False: 閉業中, None: 不明


class FavoriteStoreDAO:
    """
    お気に入り店舗 DAO（暫定：メモリ上のリストで管理）
    将来は、このクラス内部だけを DB アクセスに差し替えればよい。
    """

    _FAVORITES: List[FavoriteStore] = []

    @classmethod
    def list_by_user(cls, user_id: int) -> List[FavoriteStore]:
        """指定ユーザーのお気に入り店舗一覧を返す"""
        return [f for f in cls._FAVORITES if f.user_id == user_id]

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
        お気に入りに追加。
        すでに同じ (user_id, store_id) があれば情報を更新する。
        """
        for f in cls._FAVORITES:
            if f.user_id == user_id and f.store_id == store_id:
                f.store_name = store_name
                f.latitude = latitude
                f.longitude = longitude
                f.open_now = open_now
                return

        cls._FAVORITES.append(
            FavoriteStore(
                user_id=user_id,
                store_id=store_id,
                store_name=store_name,
                latitude=latitude,
                longitude=longitude,
                open_now=open_now,
            )
        )

    @classmethod
    def remove(cls, user_id: int, store_id: str) -> None:
        """お気に入りから削除"""
        cls._FAVORITES = [
            f for f in cls._FAVORITES
            if not (f.user_id == user_id and f.store_id == store_id)
        ]
