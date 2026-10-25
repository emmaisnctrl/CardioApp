from app import db
from datetime import datetime

class Scan(db.Model):
    # Table name in the database
    __tablename__ = 'scans'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Measurements and classification
    heart_rate = db.Column(db.Float, nullable=False)
    spo2 = db.Column(db.Float, nullable=False)              # 0 = not available
    condition = db.Column(db.String(100), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)  # 0 = rule-based result
    recommendation = db.Column(db.Text, nullable=False)

    # State chosen on the Pre-scan screen (Resting, Active or Unwell)
    pre_scan_state = db.Column(db.String(50), default='Resting')

    # Pulse analysis (only meaningful when the signal quality was good enough)
    pulse_regularity = db.Column(db.String(40), default='Not recorded')
    prv_ms = db.Column(db.Float, default=0)                 # 0 = not available
    scan_quality = db.Column(db.String(20), default='Not recorded')

    scanned_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Scan {self.id} - {self.condition}>'