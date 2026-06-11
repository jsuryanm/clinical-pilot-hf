from sqlalchemy import text
from app.db.session import SessionLocal

with SessionLocal() as s:
    rows = s.execute(text("SELECT id, name FROM patients LIMIT 20"))
    for r in rows:
        print(r)

    result = s.execute(text("SELECT COUNT(*) FROM patients"))
    print(result.scalar())

