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
