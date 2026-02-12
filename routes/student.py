from flask import Blueprint, request, jsonify
from datetime import date
from models import db, User, AttendanceSession, AttendanceRecord, TeacherSchedule

student_bp = Blueprint("student", __name__)


@student_bp.route("/active-teachers", methods=["GET"])
def active_teachers():
    """
    Returns all active attendance sessions with teacher and schedule details.
    Students will scan for the specific teacher's beacon to mark attendance.
    """
    today = date.today()

    # Get all active sessions for today
    sessions = AttendanceSession.query.filter(
        AttendanceSession.session_date == today,
        AttendanceSession.is_active == True
    ).all()

    result = []
    for session in sessions:
        teacher = User.query.get(session.teacher_id)
        schedule = TeacherSchedule.query.get(session.schedule_id)
        
        if teacher and schedule:
            result.append({
                "teacher_name": teacher.username,
                "session_id": session.id,
                "beacon_id": session.beacon_id.lower(),  # For BLE scanning
                "day": schedule.day_of_week,
                "start_time": schedule.start_time.strftime("%H:%M"),
                "end_time": schedule.end_time.strftime("%H:%M")
            })

    return jsonify(result), 200


@student_bp.route("/mark-attendance", methods=["POST"])
def mark_attendance():
    """
    Mark attendance for a student in a specific session.
    This should only be called when:
    1. Student scans the teacher's BLE beacon, OR
    2. Student manually enters the session ID
    """
    data = request.json
    username = data.get("username")
    session_id = data.get("session_id")

    if not username or not session_id:
        return jsonify({"message": "Missing username or session_id"}), 400

    student = User.query.filter_by(username=username, role="student").first()
    if not student:
        return jsonify({"message": "Student not found"}), 404

    session = AttendanceSession.query.filter_by(id=session_id, is_active=True).first()
    if not session:
        return jsonify({"message": "Attendance session not active or not found"}), 400

    # Check if attendance already marked
    existing = AttendanceRecord.query.filter_by(
        session_id=session_id,
        student_id=student.id
    ).first()

    if existing:
        return jsonify({"message": "Attendance already marked for this session"}), 400

    # Create new attendance record
    record = AttendanceRecord(
        session_id=session_id,
        student_id=student.id,
        status="present",
        manual=False  # Set to True if manually entered (could be a parameter)
    )

    db.session.add(record)
    db.session.commit()

    # Get teacher name for response
    teacher = User.query.get(session.teacher_id)
    teacher_name = teacher.username if teacher else "Unknown"

    return jsonify({
        "message": "Attendance marked successfully",
        "teacher": teacher_name,
        "session_id": session_id
    }), 200