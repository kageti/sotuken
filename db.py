# db.py
import os
from mysql.connector import pooling

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "10.16.73.200"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "appuser"),
    "password": os.getenv("DB_PASSWORD", "sotuken"),
    "database": os.getenv("DB_NAME", "sotuken"),
}

_pool = None

def get_connection():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="sotuken_pool",
            pool_size=5,
            **DB_CONFIG
        )
    return _pool.get_connection()
