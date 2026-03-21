from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from datetime import datetime
import uuid

from models import db, User, Teacher, Student, TeacherSchedule
from utils.mappers import get_teacher_by_username

admin_bp = Blueprint("admin", __name__)

VALID_DAYS = [
    "Monday","Tuesday","Wednesday",
    "Thursday","Friday","Saturday","Sunday"
]


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

    db.session.add(user)
    db.session.flush()

    if role == "teacher":
        db.session.add(Teacher(
            user_id=user.id,
            beacon_id=str(uuid.uuid4())
        ))
    else:
        db.session.add(Student(user_id=user.id))

    db.session.commit()
    return jsonify({"message": f"{role} created successfully"}), 201


@admin_bp.route("/delete-user", methods=["POST"])
def delete_user():
    username = request.json.get("username")

    user = User.query.filter_by(username=username).first()
    if not user:
        return jsonify({"message": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "User deleted successfully"}), 200


@admin_bp.route("/list-users", methods=["GET"])
def list_users():
    role = request.args.get("role")

    if role not in ["teacher", "student"]:
        return jsonify({"message": "Invalid role"}), 400

    users = User.query.filter_by(role=role).all()
    return jsonify({
        "users": [{"username": u.username, "role": u.role} for u in users]
    }), 200


@admin_bp.route("/assign-schedule", methods=["POST"])
def assign_schedule():
    data = request.json

    teacher_username = data.get("teacher_username")
    day = data.get("day")
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    teacher = get_teacher_by_username(teacher_username)
    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404

    try:
        start_t = datetime.strptime(start_time, "%H:%M").time()
        end_t = datetime.strptime(end_time, "%H:%M").time()
    except:
        return jsonify({"message": "Invalid time format"}), 400

    schedule = TeacherSchedule(
        teacher_id=teacher.id,
        day_of_week=day,
        start_time=start_t,
        end_time=end_t
    )

    db.session.add(schedule)
    db.session.commit()

    return jsonify({"message": "Schedule assigned successfully"}), 201