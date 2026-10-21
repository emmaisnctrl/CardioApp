from app import db
from datetime import datetime

class User(db.Model):
    # Define the table name in the database
    __tablename__ = 'users'

    # Primary key - unique ID for each user, auto-increments
    id = db.Column(db.Integer, primary_key=True)
    
    # User's full name
    username = db.Column(db.String(100), nullable=False)
    
    # User's email - must be unique, used for login and password reset
    email = db.Column(db.String(150), unique=True, nullable=False)
    
    # Hashed password - we never store plain text passwords
    password = db.Column(db.String(200), nullable=False)
    
    # Date and time the account was created, set automatically
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Link this user to their scans in the scan table
    # 'lazy=True' means scans are only loaded from the database when accessed
    scans = db.relationship('Scan', backref='user', lazy=True)

    def __repr__(self):
        # This controls how a User object is displayed when printed
        return f'<User {self.email}>'