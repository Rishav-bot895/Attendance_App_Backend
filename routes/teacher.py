from flask import Blueprint, request, jsonify
from datetime import datetime, date, time, timedelta
from models import db, User, TeacherSchedule, AttendanceSession, AttendanceRecord

teacher_bp = Blueprint("teacher", __name__)


@teacher_bp.route("/start-attendance", methods=["POST"])
def start_attendance():
    username = request.json.get("username")

    teacher = User.query.filter_by(username=username, role="teacher").first()
    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404

    now = datetime.now()
    today = date.today()
    day = now.strftime("%A")
    current_time = now.time()

    # Get all schedules for this teacher on this day
    schedules = TeacherSchedule.query.filter_by(
        teacher_id=teacher.id,
        day_of_week=day
    ).all()

    if not schedules:
        return jsonify({"message": "No schedule assigned for today"}), 403

    # ✅ FLEXIBLE TIME CHECK: Allow starting attendance if teacher has ANY schedule today
    # This allows multiple teachers with overlapping schedules to start independently
    # Teacher can start within ±30 minutes of any of their scheduled periods
    
    valid_schedule = None
    BUFFER_MINUTES = 30  # Allow starting 30 min before or after scheduled time
    
    for schedule in schedules:
        # Calculate time window with buffer
        start_with_buffer = (datetime.combine(today, schedule.start_time) - timedelta(minutes=BUFFER_MINUTES)).time()
        end_with_buffer = (datetime.combine(today, schedule.end_time) + timedelta(minutes=BUFFER_MINUTES)).time()
        
        # Check if current time is within the buffered window
        if start_with_buffer <= current_time <= end_with_buffer:
            valid_schedule = schedule
            break
    
    # If no schedule found within buffer, just use the first schedule
    # This allows teachers to start attendance whenever they want if they have a schedule today
    if not valid_schedule:
        valid_schedule = schedules[0]  # Use first schedule as fallback

    # 🔒 Close ONLY this teacher's previous active sessions
    # This ensures each teacher's sessions are independent
    AttendanceSession.query.filter_by(
        teacher_id=teacher.id,
        is_active=True
    ).update({"is_active": False})
    db.session.commit()

    # ✅ Create NEW session with unique beacon_id
    # Each session uses the teacher's unique beacon_id
    # This ensures students can ONLY mark attendance for the specific teacher they scan
    session = AttendanceSession(
        teacher_id=teacher.id,
        schedule_id=valid_schedule.id,
        session_date=today,
        is_active=True,
        beacon_id=teacher.beacon_id.lower()  # Unique per teacher
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


@teacher_bp.route("/close-attendance", methods=["POST"])
def close_attendance():
    session_id = request.json.get("session_id")
    session = AttendanceSession.query.get(session_id)

    if not session:
        return jsonify({"message": "Session not found"}), 404

    session.is_active = False
    db.session.commit()

    return jsonify({"message": "Attendance session closed"}), 200