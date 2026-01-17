from flask import Blueprint, request, jsonify
from datetime import datetime

from models import db, User, TeacherSchedule, AttendanceSession, AttendanceRecord

teacher_bp = Blueprint("teacher", __name__)


@teacher_bp.route("/start-attendance", methods=["POST"])
def start_attendance():
    data = request.json
    username = data.get("username")

    teacher = User.query.filter_by(username=username, role="teacher").first()
    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404

    now = datetime.now()
    today = now.date()
    current_day = now.strftime("%A")
    current_time = now.strftime("%H:%M")

    # Find the CURRENT schedule slot
    schedule = TeacherSchedule.query.filter(
        TeacherSchedule.teacher_id == teacher.id,
        TeacherSchedule.day_of_week == current_day,
        TeacherSchedule.start_time <= current_time,
        TeacherSchedule.end_time >= current_time
    ).first()

    if not schedule:
        return jsonify({"message": "Not within assigned schedule"}), 403

    # 🔁 Check if session already exists for THIS slot and date
    session = AttendanceSession.query.filter_by(
        teacher_id=teacher.id,
        schedule_id=schedule.id,
        session_date=today
    ).first()

    if session:
        # Reopen existing session
        session.is_active = True
        db.session.commit()

        return jsonify({
            "message": "Attendance session resumed",
            "session_id": session.id
        }), 200

    # Create new session (first time only)
    session = AttendanceSession(
        teacher_id=teacher.id,
        schedule_id=schedule.id,
        session_date=today,
        is_active=True
    )

    db.session.add(session)
    db.session.commit()

    return jsonify({
        "message": "Attendance session started",
        "session_id": session.id
    }), 201


@teacher_bp.route("/close-attendance", methods=["POST"])
def close_attendance():
    data = request.json
    session_id = data.get("session_id")

    session = AttendanceSession.query.get(session_id)
    if not session:
        return jsonify({"message": "Session not found"}), 404

    session.is_active = False
    db.session.commit()

    return jsonify({"message": "Attendance session closed"}), 200


@teacher_bp.route("/absent-students", methods=["GET"])
def absent_students():
    session_id = request.args.get("session_id")

    session = AttendanceSession.query.get(session_id)
    if not session:
        return jsonify({"message": "Session not found"}), 404

    students = User.query.filter_by(role="student").all()
    absentees = []

    for s in students:
        record = AttendanceRecord.query.filter_by(
            session_id=session.id,
            student_id=s.id
        ).first()

        if not record:
            absentees.append(s.username)

    return jsonify(absentees), 200


@teacher_bp.route("/mark-present", methods=["POST"])
def mark_present():
    data = request.json
    session_id = data.get("session_id")
    student_username = data.get("student_username")

    student = User.query.filter_by(username=student_username, role="student").first()
    if not student:
        return jsonify({"message": "Student not found"}), 404

    record = AttendanceRecord.query.filter_by(
        session_id=session_id,
        student_id=student.id
    ).first()

    if record:
        record.status = "present"
        record.manual = True
    else:
        record = AttendanceRecord(
            session_id=session_id,
            student_id=student.id,
            status="present",
            manual=True
        )
        db.session.add(record)

    db.session.commit()

    return jsonify({"message": "Student marked present"}), 200
