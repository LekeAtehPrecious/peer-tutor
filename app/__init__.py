from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Initialise extensions
db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configuration settings
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///peertutor.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "peertutor-secret-key"

    # Initialise extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "main.login"
    login_manager.login_message = "Please login to access this page."
    login_manager.login_message_category = "info"

    # Register Blueprints
    from app.routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    return app