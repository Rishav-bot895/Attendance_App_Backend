from flask import Blueprint, request, jsonify
from datetime import date
from models import db, User, AttendanceSession, AttendanceRecord

student_bp = Blueprint("student", __name__)


@student_bp.route("/active-teachers", methods=["GET"])
def active_teachers():
    today = date.today()

    sessions = AttendanceSession.query.filter_by(
        session_date=today,
        is_active=True
    ).all()

    result = []
    for s in sessions:
        teacher = User.query.get(s.teacher_id)
        result.append({
            "teacher_name": teacher.username,
            "session_id": s.id,
            "beacon_id": s.beacon_id
        })

    return jsonify(result), 200


@student_bp.route("/mark-attendance", methods=["POST"])
def mark_attendance():
    data = request.json
    username = data.get("username")
    session_id = data.get("session_id")

    student = User.query.filter_by(username=username, role="student").first()
    if not student:
        return jsonify({"message": "Student not found"}), 404

    session = AttendanceSession.query.filter_by(id=session_id, is_active=True).first()
    if not session:
        return jsonify({"message": "Attendance session not active"}), 400

    existing = AttendanceRecord.query.filter_by(
        session_id=session_id,
        student_id=student.id
    ).first()

    if existing:
        return jsonify({"message": "Attendance already marked"}), 400

    record = AttendanceRecord(
        session_id=session_id,
        student_id=student.id,
        status="present"
    )

    db.session.add(record)
    db.session.commit()

    return jsonify({"message": "Attendance marked present"}), 200
