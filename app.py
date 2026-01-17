import os
from flask import Flask
from flask_cors import CORS

from config import Config
from models import db

from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.teacher import teacher_bp
from routes.student import student_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app)

    db.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(teacher_bp, url_prefix="/teacher")
    app.register_blueprint(student_bp, url_prefix="/student")

    with app.app_context():
        db.create_all()

    return app


# 🔴 THIS LINE IS REQUIRED FOR GUNICORN
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
