from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, date

from models import db, TeacherSchedule, AttendanceSession, AttendanceRecord, Student
from utils.mappers import get_teacher_by_username, get_student_by_username
import csv
from io import StringIO, BytesIO

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


@teacher_bp.route("/all-students-status", methods=["GET"])
def all_students_status():
    """Returns all students with their attendance status for a given session."""
    session_id = request.args.get("session_id")
    session = AttendanceSession.query.get(session_id)

    if not session or not session.is_active:
        return jsonify({"message": "Session not found"}), 404

    students = Student.query.all()
    result = []

    for s in students:
        record = AttendanceRecord.query.filter_by(
            session_id=session.id,
            student_id=s.id
        ).first()

        result.append({
            "username": s.user.username,
            "status": record.status if record else "absent",
            "manual": record.manual if record else False,
        })

   
    result.sort(key=lambda x: x["username"])

    return jsonify(result), 200


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


@teacher_bp.route("/mark-absent", methods=["POST"])
def mark_absent():
    """Manually mark a student as absent."""
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
        record.status = "absent"
        record.manual = True
    else:
        db.session.add(AttendanceRecord(
            session_id=session_id,
            student_id=student.id,
            status="absent",
            manual=True
        ))

    db.session.commit()
    return jsonify({"message": "Student marked absent"}), 200


@teacher_bp.route("/close-attendance", methods=["POST"])
def close_attendance():
    session_id = request.json.get("session_id")
    session = AttendanceSession.query.get(session_id)

    if not session:
        return jsonify({"message": "Session not found"}), 404

    session.is_active = False
    db.session.commit()

    return jsonify({"message": "Attendance session closed"}), 200


@teacher_bp.route("/download-attendance", methods=["GET"])
def download_attendance():
    session_id = request.args.get("session_id")

    session = AttendanceSession.query.get(session_id)
    if not session:
        return jsonify({"message": "Session not found"}), 404

    from models import Teacher
    teacher = Teacher.query.get(session.teacher_id)
    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404

    students = Student.query.all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["student_username", "status", "manual"])

    for s in students:
        record = AttendanceRecord.query.filter_by(
            session_id=session.id,
            student_id=s.id
        ).first()

        if record:
            writer.writerow([s.user.username, record.status, record.manual])
        else:
            writer.writerow([s.user.username, "absent", False])

    mem = BytesIO()
    mem.write(output.getvalue().encode())
    mem.seek(0)

    filename = f"{teacher.user.username}_{session.session_date}_{datetime.now().strftime('%H-%M')}.csv"

    return send_file(
        mem,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename
    )