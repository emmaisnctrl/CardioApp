from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cardioapp-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///cardioapp.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'cardioapp-jwt-secret-2024'
    
    # Email config for forgot password
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_USERNAME')
    
# Initialize extensions without attaching them to an app yet
# They will be properly connected to the app inside create_app()
db = SQLAlchemy()      # Handles the SQLite database
bcrypt = Bcrypt()      # Handles password hashing
jwt = JWTManager()     # Handles login tokens (keeps users logged in)
mail = Mail()          # Handles sending emails (forgot password)

def create_app():
    # Create the Flask application instance
    app = Flask(__name__)
    
    # Load configuration settings from config.py
    app.config.from_object(Config)

    # Connect each extension to the app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    # Import the route files (auth and scan endpoints)
    from app.routes.auth import auth
    from app.routes.scan import scan

    # Register the routes with a URL prefix
    # e.g. auth routes will be at /auth/register, /auth/login etc.
    # e.g. scan routes will be at /scan/start etc.
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(scan, url_prefix='/scan')

    # Create all database tables if they don't exist yet
    with app.app_context():
        db.create_all()

    return app