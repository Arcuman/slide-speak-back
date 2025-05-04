from flask import Flask
from flask_cors import CORS


def create_app():
    app = Flask(__name__)
    app.response_buffering = False
    CORS(app)

    # Import and register blueprints
    from app.api.routes import api_bp

    app.register_blueprint(api_bp)
    return app
