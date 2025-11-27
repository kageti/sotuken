# db.py
import mysql.connector
from mysql.connector import pooling


DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "password",
    "database": "sotuken",
}

# コネクションプール（同時アクセスにも強くなる）
connection_pool = pooling.MySQLConnectionPool(
    pool_name="sotuken_pool",
    pool_size=5,
    **DB_CONFIG
)

def get_connection():
    
    return connection_pool.get_connection()
