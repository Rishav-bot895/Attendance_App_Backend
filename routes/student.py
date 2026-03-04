from flask import Blueprint, request, jsonify
from datetime import date

from models import db, AttendanceSession, AttendanceRecord, TeacherSchedule, Teacher
from utils.mappers import get_student_by_username

student_bp = Blueprint("student", __name__)


@student_bp.route("/active-teachers", methods=["GET"])
def active_teachers():
    today = date.today()

    sessions = AttendanceSession.query.filter(
        AttendanceSession.session_date == today,
        AttendanceSession.is_active == True
    ).all()

    result = []
    for session in sessions:
        teacher = Teacher.query.get(session.teacher_id)  # ✅ FIXED (source of truth)
        schedule = TeacherSchedule.query.get(session.schedule_id)

        if teacher and schedule:
            result.append({
                "teacher_name": teacher.user.username,
                "session_id": session.id,
                "beacon_id": session.beacon_id.lower(),
                "day": schedule.day_of_week,
                "start_time": schedule.start_time.strftime("%H:%M"),
                "end_time": schedule.end_time.strftime("%H:%M")
            })

    return jsonify(result), 200


@student_bp.route("/mark-attendance", methods=["POST"])
def mark_attendance():
    data = request.json
    username = data.get("username")
    session_id = data.get("session_id")

    student = get_student_by_username(username)
    if not student:
        return jsonify({"message": "Student not found"}), 404

    session = AttendanceSession.query.filter_by(id=session_id, is_active=True).first()
    if not session:
        return jsonify({"message": "Attendance session not active or not found"}), 400

    existing = AttendanceRecord.query.filter_by(
        session_id=session_id,
        student_id=student.id
    ).first()

    if existing:
        return jsonify({"message": "Attendance already marked for this session"}), 400

    db.session.add(AttendanceRecord(
        session_id=session_id,
        student_id=student.id,
        status="present",
        manual=False
    ))
    db.session.commit()

    teacher = Teacher.query.get(session.teacher_id)

    return jsonify({
        "message": "Attendance marked successfully",
        "teacher": teacher.user.username if teacher else "Unknown",
        "session_id": session_id
    }), 200