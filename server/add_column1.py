from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()

NEW_COLUMNS = {
    "pulse_regularity": "VARCHAR(40) DEFAULT 'Not recorded'",
    "prv_ms": "FLOAT DEFAULT 0",
    "scan_quality": "VARCHAR(20) DEFAULT 'Not recorded'",
}

with app.app_context():
    existing = [c['name'] for c in inspect(db.engine).get_columns('scans')]
    for name, ddl in NEW_COLUMNS.items():
        if name in existing:
            print(name, "already exists")
        else:
            db.session.execute(text(f"ALTER TABLE scans ADD COLUMN {name} {ddl}"))
            print("added", name)
    db.session.commit()