from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    cols = [c['name'] for c in inspect(db.engine).get_columns('scans')]
    if 'pre_scan_state' in cols:
        print("Column already exists. Nothing to do.")
    else:
        db.session.execute(text(
            "ALTER TABLE scans ADD COLUMN pre_scan_state VARCHAR(50) DEFAULT 'Not recorded'"
        ))
        db.session.commit()
        print("Column added. Old scans now show 'Not recorded'.")