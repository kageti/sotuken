# dao/store_dao.py
from typing import List, Optional
from db import get_connection

class Store:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name

class StoreDAO:

    @staticmethod
    def find_all() -> List[Store]:
        sql = "SELECT id, name FROM stores ORDER BY name"
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql)
                rows = cur.fetchall()
            return [Store(**row) for row in rows]
        finally:
            conn.close()

    @staticmethod
    def insert(name: str) -> int:
        sql = "INSERT INTO stores (name) VALUES (%s)"
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (name,))
            conn.commit()
            return cur.lastrowid
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
