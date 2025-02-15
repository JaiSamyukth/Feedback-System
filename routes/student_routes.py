from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils import get_student_info, has_submitted_feedback, append_ratings, load_admin_mapping
from config import FEEDBACK_QUESTIONS

student_bp = Blueprint('student', __name__)

@student_bp.route('/', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        registerno = request.form.get('registerno')
        if not registerno:
            flash("Please enter your registration number.", "danger")
        else:
            student_info = get_student_info(registerno.strip())
            if not student_info:
                flash("Registration number not found. Please try again.", "danger")
            else:
                department = student_info.get('department')
                semester = student_info.get('semester')
                return redirect(url_for('student.feedback', department=department, 
                                      semester=semester, registerno=registerno))
    return render_template('student_login.html')

@student_bp.route('/feedback', methods=['GET', 'POST'])
def feedback():
    department = request.args.get('department')
    semester = request.args.get('semester')
    registerno = request.args.get('registerno')

    if not department or not semester or not registerno:
        flash("Missing department, semester, or registration number.", "danger")
        return redirect(url_for('student.student_login'))

    if has_submitted_feedback(registerno):
        flash("Feedback already submitted. You have already registered.", "info")
        return redirect(url_for('student.student_login'))

    mappings = load_admin_mapping(department, semester)
    if not mappings:
        return f"<h2>No staff/subject mappings found for {department} - {semester}.</h2>"

    if request.method == 'POST':
        if has_submitted_feedback(registerno):
            flash("Feedback already submitted. You have already registered.", "info")
            return redirect(url_for('student.student_login'))

        rating_rows = []
        error_flag = False

        for idx, mapping in enumerate(mappings):
            ratings = []
            for q in range(1, 11):
                key = f"rating-{idx}-{q}"
                value = request.form.get(key)
                if not value:
                    flash(f"Please fill all rating boxes for {mapping['staff']}.", "danger")
                    error_flag = True
                    break
                try:
                    score = float(value)
                except ValueError:
                    flash(f"Invalid rating value for {mapping['staff']}.", "danger")
                    error_flag = True
                    break
                ratings.append(score)

            if error_flag:
                break

            average = sum(ratings) / len(ratings)
            rating_rows.append({
                'registerno': registerno,
                'department': department,
                'semester': semester,
                'staff': mapping['staff'],
                'subject': mapping['subject'],
                'average': f"{average:.2f}"
            })

        if error_flag:
            return redirect(url_for('student.feedback', department=department, 
                                  semester=semester, registerno=registerno))
        else:
            append_ratings(rating_rows)
            flash("Feedback submitted successfully. Thank you!", "success")
            return redirect(url_for('student.student_login'))

    return render_template('feedback_form.html',
                         department=department,
                         semester=semester,
                         mappings=mappings,
                         questions=FEEDBACK_QUESTIONS)