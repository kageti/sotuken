"""DAO for users table."""
from datetime import datetime
from typing import Optional

from mysql.connector import IntegrityError, errorcode
from werkzeug.security import generate_password_hash

from db import get_connection


class UserAlreadyExists(Exception):
    """Raised when trying to create a user with an existing email."""


class User:
    def __init__(self, id: int, email: str, password_hash: str, created_at: datetime):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.created_at = created_at


class UserDAO:
    @staticmethod
    def find_by_email(email: str) -> Optional[User]:
        sql = """
            SELECT id, email, password_hash, created_at
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
        sql = """
            INSERT INTO users (email, password_hash)
            VALUES (%s, %s)
        """
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (email, password_hash))
                conn.commit()
        except IntegrityError as e:
            if e.errno == errorcode.ER_DUP_ENTRY:
                raise UserAlreadyExists() from e
            raise
        finally:
            conn.close()

        created = UserDAO.find_by_email(email)
        if created is None:
            raise RuntimeError("Failed to fetch the created user.")
        return created
