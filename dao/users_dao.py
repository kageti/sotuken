"""DAO for users table."""
from datetime import datetime
from typing import Optional
import random
import string

from mysql.connector import IntegrityError, errorcode
from werkzeug.security import generate_password_hash

from db import get_connection


class UserAlreadyExists(Exception):
    """Raised when trying to create a user with an existing email."""


class User:
    def __init__(self, id: int, email: str, password_hash: str,
                 user_id: str, created_at: datetime):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.user_id = user_id
        self.created_at = created_at


class UserDAO:

    @staticmethod
    def _generate_user_id() -> str:
        """8桁のランダム数字を生成"""
        return "".join(random.choices(string.digits, k=8))

    @staticmethod
    def find_by_email(email: str) -> Optional[User]:
        sql = """
            SELECT id, email, password_hash, user_id, created_at
            FROM users
            WHERE email = %s
        """
        conn = get_connection()
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, (email,))
                row = cur.fetchone()
                if row is None:
                    return None
                return User(**row)
        finally:
            conn.close()

    @staticmethod
    def create_user(email: str, password: str) -> User:
        password_hash = generate_password_hash(password)

        # ★ ここでランダム8桁ID生成！
        user_id = UserDAO._generate_user_id()

        sql = """
            INSERT INTO users (email, password_hash, user_id)
            VALUES (%s, %s, %s)
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (email, password_hash, user_id))
                conn.commit()
        except IntegrityError as e:
            if e.errno == errorcode.ER_DUP_ENTRY:
                raise UserAlreadyExists() from e
            raise
        finally:
            conn.close()

        # 登録したユーザーを返す
        created = UserDAO.find_by_email(email)
        if created is None:
            raise RuntimeError("Failed to fetch the created user.")
        return created
