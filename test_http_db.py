import os
from dotenv import load_dotenv
load_dotenv()

from database import get_db_connection

def test_db():
    print("Testing Turso HTTP Database Connection...")
    conn = get_db_connection()
    cur = conn.cursor()
    print("Executing query...")
    cur.execute("SELECT 1")
    res = cur.fetchone()
    print("Result of SELECT 1:", res)
    assert res is not None
    assert res[0] == 1
    print("Database works successfully!")

if __name__ == "__main__":
    test_db()
