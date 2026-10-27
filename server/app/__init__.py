import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_mail import Mail

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()
mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_pyfile("../config.py")
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False

    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config["SQLALCHEMY_DATABASE_URI"] = database_url

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", app.config.get("SECRET_KEY"))
    app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", app.config.get("JWT_SECRET_KEY"))

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    from app.routes.auth import auth
    from app.routes.scan import scan

    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(scan, url_prefix="/scan")

    with app.app_context():
        db.create_all()

    return app
