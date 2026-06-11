from sqlalchemy import text
from app.db.session import SessionLocal

with SessionLocal() as s:
    result = s.execute(text("""
        SELECT enumlabel
        FROM pg_enum e
        JOIN pg_type t ON e.enumtypid = t.oid
        WHERE t.typname = 'booking_status'
    """))

    print("booking_status enum values:")
    for row in result:
        print(row[0])