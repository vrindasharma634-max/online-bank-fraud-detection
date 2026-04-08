"""
CryptoGuard Backend - Flask Application
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import importlib.util
import os

if importlib.util.find_spec("flask_cors") is not None:
    CORS = __import__("flask_cors", fromlist=["CORS"]).CORS
else:
    def CORS(app, **kwargs):
        return app

try:
    from flask_jwt_extended import JWTManager
except ImportError:
    class JWTManager:
        def init_app(self, app):
            return None

try:
    from flask_bcrypt import Bcrypt
except ImportError:
    from werkzeug.security import check_password_hash as _check_password_hash, generate_password_hash as _generate_password_hash

    class Bcrypt:
        def init_app(self, app):
            return None

        def generate_password_hash(self, password, **kwargs):
            return _generate_password_hash(password, **kwargs)

        def check_password_hash(self, pw_hash, password):
            return _check_password_hash(pw_hash, password)

db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'templates'),
        static_folder=os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static')
    )

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cryptoguard-dev-secret-2024')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-cryptoguard-secret-2024')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(
        os.path.dirname(__file__), '..', 'cryptoguard.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 hours

    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app, supports_credentials=True)

    from backend.routes.auth import auth_bp
    from backend.routes.predict import predict_bp
    from backend.routes.dashboard import dashboard_bp
    from backend.routes.pages import pages_bp
    from backend.routes.url_checker_route import url_checker_bp

    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(predict_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/api')
    app.register_blueprint(url_checker_bp, url_prefix='/api')
    app.register_blueprint(pages_bp)

    with app.app_context():
        db.create_all()

    return app