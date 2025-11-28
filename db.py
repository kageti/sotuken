# db.py
import mysql.connector
from mysql.connector import pooling


DB_CONFIG = {
    "host": "10.16.73.155",
    "port": 3306,
    "user": "appuser",
    "password": "sotuken",
    "database": "sotuken",
    "auth_plugin": "mysql_native_password",
}

# コネクションプール（同時アクセスにも強くなる）
connection_pool = pooling.MySQLConnectionPool(
    pool_name="sotuken_pool",
    pool_size=5,
    **DB_CONFIG
)

def get_connection():
    
    return connection_pool.get_connection()
