import sqlite3
import db

conn = sqlite3.connect(":memory:")
print(db.check_or_register(conn, "테스트", "1234"))  # True (새로 등록)
print(db.check_or_register(conn, "테스트", "1234"))  # True (PIN 일치)
print(db.check_or_register(conn, "테스트", "9999"))  # False (PIN 불일치)