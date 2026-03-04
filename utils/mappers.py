from models import User


def get_teacher_by_username(username):
    user = User.query.filter_by(username=username, role="teacher").first()
    return user.teacher_profile if user else None


def get_student_by_username(username):
    user = User.query.filter_by(username=username, role="student").first()
    return user.student_profile if user else None


def get_teacher_by_user_id(user_id):
    user = User.query.get(user_id)
    if not user or user.role != "teacher":
        return None
    return user.teacher_profile


def get_student_by_user_id(user_id):
    user = User.query.get(user_id)
    if not user or user.role != "student":
        return None
    return user.student_profile