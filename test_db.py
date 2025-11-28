import mysql.connector

conn = mysql.connector.connect(
    host="10.16.73.155",      # あなたのPCのIP
    user="appuser",
    password="sotuken",
    database="sotuken",
    auth_plugin="mysql_native_password"
)

print("接続成功！")
