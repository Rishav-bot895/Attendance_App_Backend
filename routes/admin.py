from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from datetime import datetime
import uuid

from models import db, User, TeacherSchedule

admin_bp = Blueprint("admin", __name__)

VALID_DAYS = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday", "Saturday", "Sunday"
]


# -----------------------------
# CREATE USER
# -----------------------------
@admin_bp.route("/create-user", methods=["POST"])
def create_user():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    role = data.get("role")

    if not username or not password or not role:
        return jsonify({"message": "Missing fields"}), 400

    if role not in ["teacher", "student"]:
        return jsonify({"message": "Invalid role"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"message": "User already exists"}), 400

    user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role
    )

    # 🔑 BLE UUID generated ONCE for teachers
    if role == "teacher":
        user.beacon_id = str(uuid.uuid4())

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": f"{role} created successfully"}), 201


# -----------------------------
# DELETE USER
# -----------------------------
@admin_bp.route("/delete-user", methods=["POST"])
def delete_user():
    data = request.json
    username = data.get("username")

    if not username:
        return jsonify({"message": "Username required"}), 400

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    if user.role == "teacher":
        TeacherSchedule.query.filter_by(teacher_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "User deleted successfully"}), 200


# -----------------------------
# ASSIGN SCHEDULE
# -----------------------------
@admin_bp.route("/assign-schedule", methods=["POST"])
def assign_schedule():
    data = request.json

    teacher_username = data.get("teacher_username")
    day = data.get("day")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not teacher_username or not day or not start_time or not end_time:
        return jsonify({"message": "Missing fields"}), 400

    if day not in VALID_DAYS:
        return jsonify({"message": "Invalid day"}), 400

    try:
        start_t = datetime.strptime(start_time, "%H:%M").time()
        end_t = datetime.strptime(end_time, "%H:%M").time()
    except ValueError:
        return jsonify({"message": "Invalid time format"}), 400

    if start_t >= end_t:
        return jsonify({"message": "Start time must be before end time"}), 400

    teacher = User.query.filter_by(username=teacher_username, role="teacher").first()
    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404

    schedule = TeacherSchedule(
        teacher_id=teacher.id,
        day_of_week=day,
        start_time=start_t,
        end_time=end_t
    )

    db.session.add(schedule)
    db.session.commit()

    return jsonify({"message": "Schedule assigned successfully"}), 201
