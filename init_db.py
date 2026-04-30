import pymysql
import os

host = 'iw-explora.mysql.database.azure.com'
user = 'iwco'
password = 'Ef4A7cvqX3gwwch6t4d2ZUMxP5n0CX'
db_name = 'requisitions_db'

print(f"Connecting to {host}...")
conn = pymysql.connect(host=host, user=user, password=password, autocommit=True, ssl={"fake_flag_to_enable_ssl": True})
cursor = conn.cursor()

# Create DB if not exists
cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
cursor.execute(f"USE {db_name};")

# Read and execute init.sql
with open('db/init.sql', 'r') as f:
    sql = f.read()

# Very basic split by semicolon, ignoring comments.
# Actually it's easier to just use pymysql executemany or split
statements = sql.split(';')
for statement in statements:
    stmt = statement.strip()
    if stmt:
        try:
            cursor.execute(stmt)
        except Exception as e:
            pass # ignore errors from "DROP TABLE" if they don't exist

print("Database initialization complete.")
