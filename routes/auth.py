from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

from models import User

auth_bp = Blueprint("auth", __name__)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("admin123")


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json

    if not data:
        return jsonify({"message": "No data provided"}), 400

    username = data.get("username")
    password = data.get("password")
    role = data.get("role")

    # -------- ADMIN LOGIN --------
    if role == "admin":
        if (
            username == ADMIN_USERNAME
            and check_password_hash(ADMIN_PASSWORD_HASH, password)
        ):
            return jsonify({
                "message": "Admin login successful",
                "role": "admin",
                "username": ADMIN_USERNAME
            }), 200

        return jsonify({"message": "Invalid admin credentials"}), 401

    # -------- TEACHER / STUDENT LOGIN --------
    user = User.query.filter_by(username=username, role=role).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid credentials"}), 401

    return jsonify({
        "message": "Login successful",
        "role": user.role,
        "user_id": user.id,
        "username": user.username   # 🔴 THIS FIX UNBLOCKS EVERYTHING
    }), 200
