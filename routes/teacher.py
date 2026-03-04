from flask import Blueprint, request, jsonify
from datetime import datetime, date

from models import db, TeacherSchedule, AttendanceSession, AttendanceRecord, Student
from utils.mappers import get_teacher_by_username, get_student_by_username

teacher_bp = Blueprint("teacher", __name__)


@teacher_bp.route("/start-attendance", methods=["POST"])
def start_attendance():
    username = request.json.get("username")
    teacher = get_teacher_by_username(username)

    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404

    today = date.today()
    day = datetime.now().strftime("%A")

    schedules = TeacherSchedule.query.filter_by(
        teacher_id=teacher.id,
        day_of_week=day
    ).all()

    if not schedules:
        return jsonify({"message": "No schedule assigned for today"}), 403

    valid_schedule = schedules[0]

    # ⭐ NEW — check existing session
    existing = AttendanceSession.query.filter_by(
        teacher_id=teacher.id,
        schedule_id=valid_schedule.id,
        session_date=today
    ).order_by(AttendanceSession.id.desc()).first()

    if existing:
        existing.is_active = True
        db.session.commit()

        return jsonify({
            "session_id": existing.id,
            "beacon_id": existing.beacon_id
        }), 200

    # create new session
    session = AttendanceSession(
        teacher_id=teacher.id,
        schedule_id=valid_schedule.id,
        session_date=today,
        is_active=True,
        beacon_id=teacher.beacon_id
    )

    db.session.add(session)
    db.session.commit()

    return jsonify({
        "session_id": session.id,
        "beacon_id": session.beacon_id
    }), 201

@teacher_bp.route("/absent-students", methods=["GET"])
def absent_students():
    session_id = request.args.get("session_id")
    session = AttendanceSession.query.get(session_id)

    if not session or not session.is_active:
        return jsonify({"message": "Session not found"}), 404

    students = Student.query.all()
    absentees = []

    for s in students:
        record = AttendanceRecord.query.filter_by(
            session_id=session.id,
            student_id=s.id
        ).first()

        if not record:
            absentees.append(s.user.username)

    return jsonify(absentees), 200


@teacher_bp.route("/mark-present", methods=["POST"])
def mark_present():
    data = request.json
    session_id = data.get("session_id")
    student_username = data.get("student_username")

    student = get_student_by_username(student_username)
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
        db.session.add(AttendanceRecord(
            session_id=session_id,
            student_id=student.id,
            status="present",
            manual=True
        ))

    db.session.commit()
    return jsonify({"message": "Student marked present"}), 200


@teacher_bp.route("/close-attendance", methods=["POST"])
def close_attendance():
    session_id = request.json.get("session_id")
    session = AttendanceSession.query.get(session_id)

    if not session:
        return jsonify({"message": "Session not found"}), 404

    session.is_active = False
    db.session.commit()

    return jsonify({"message": "Attendance session closed"}), 200