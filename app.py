import os
import csv
from flask import Flask, render_template, request, redirect, url_for, flash
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
from routes.hod_routes import hod_bp

from utils import (
    read_csv_as_list, load_admin_mapping, update_admin_mappings,
    append_ratings, get_student_info, has_submitted_feedback, update_mainratings
)
from config import (
    DEPARTMENTS_FILE, SEMESTERS_FILE, STAFFS_FILE, SUBJECTS_FILE,
    REQUIRED_FILES, FEEDBACK_QUESTIONS, STUDENT_FILE
)

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production
app.register_blueprint(hod_bp)

@app.route('/', methods=['GET', 'POST'])
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
                return redirect(url_for('feedback', department=department, semester=semester, registerno=registerno))
    return render_template('student_login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'vsbec':
            return redirect(url_for('admin'))
        else:
            flash("Incorrect password.", "danger")
            return redirect(url_for('admin_login'))
    return render_template('admin_login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    staffs = read_csv_as_list(STAFFS_FILE)
    subjects = read_csv_as_list(SUBJECTS_FILE)

    if request.method == 'POST':
        department = request.form.get('department')
        semester = request.form.get('semester')
        staff_list = request.form.getlist('staff')
        subject_list = request.form.getlist('subject')
        new_mappings = [{
            'department': department,
            'semester': semester,
            'staff': staff.strip(),
            'subject': subject.strip()
        } for staff, subject in zip(staff_list, subject_list) 
          if staff.strip() and subject.strip()]

        if not new_mappings:
            flash("Please enter at least one valid staff–subject mapping.", "danger")
        else:
            update_admin_mappings(department, semester, new_mappings)
            flash("Mapping(s) saved successfully.", "success")
            return redirect(url_for('admin'))

    return render_template('admin_mapping.html',
                         departments=departments,
                         semesters=semesters,
                         staffs=staffs,
                         subjects=subjects)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    department = request.args.get('department')
    semester = request.args.get('semester')
    registerno = request.args.get('registerno')

    if not department or not semester or not registerno:
        flash("Missing department, semester, or registration number.", "danger")
        return redirect(url_for('student_login'))

    if has_submitted_feedback(registerno):
        flash("Feedback already submitted. You have already registered.", "info")
        return redirect(url_for('student_login'))

    mappings = load_admin_mapping(department, semester)
    if not mappings:
        return f"<h2>No staff/subject mappings found for {department} - {semester}.</h2>"

    if request.method == 'POST':
        if has_submitted_feedback(registerno):
            flash("Feedback already submitted. You have already registered.", "info")
            return redirect(url_for('student_login'))

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
            return redirect(url_for('feedback', department=department, 
                                  semester=semester, registerno=registerno))
        else:
            append_ratings(rating_rows)
            flash("Feedback submitted successfully. Thank you!", "success")
            return redirect(url_for('student_login'))

    return render_template('feedback.html',
                         department=department,
                         semester=semester,
                         mappings=mappings,
                         questions=FEEDBACK_QUESTIONS)

# Add students route
@app.route('/addStudents', methods=['POST'])
def add_students():
    department = request.form.get('department')
    semester = request.form.get('semester')
    start_reg = request.form.get('startReg')
    end_reg = request.form.get('endReg')
    
    if not (department and semester and start_reg and end_reg):
        flash("All fields are required for adding students.", "danger")
        return redirect(url_for('admin'))
    
    try:
        start_num = int(start_reg)
        end_num = int(end_reg)
    except ValueError:
        flash("Registration numbers must be numeric.", "danger")
        return redirect(url_for('admin'))
    
    if start_num > end_num:
        flash("Start registration number must be less than or equal to end registration number.", "danger")
        return redirect(url_for('admin'))
        
    if (end_num - start_num) > 100:
        flash("Difference between start and end registration numbers is too high. Please check again.", "danger")
        return redirect(url_for('admin'))
    
    # Extract numeric semester (e.g., from 'Semester 4' or '4')
    sem_clean = semester.strip().split()[-1]
    
    # Read existing records (if any)
    records = []
    if os.path.exists(STUDENT_FILE):
        with open(STUDENT_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
    
    # Determine new registration numbers to be added
    new_regs = {str(reg) for reg in range(start_num, end_num + 1)}
    # Remove any duplicates in existing records
    filtered_records = [row for row in records if row.get('registerno') not in new_regs]
    
    # Append new records
    for reg in range(start_num, end_num + 1):
        filtered_records.append({
            'registerno': str(reg),
            'department': department.strip(),
            'semester': sem_clean
        })
    
    # Write updated records back to student.csv
    with open(STUDENT_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['registerno', 'department', 'semester']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in filtered_records:
            writer.writerow(row)
    
    flash(f"Students added/updated successfully ({start_num} to {end_num}).", "success")
    return redirect(url_for('admin'))

if __name__ == '__main__':
    # Create CSV files if they don't exist
    for file, headers in REQUIRED_FILES.items():
        if not os.path.exists(file):
            with open(file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

    app.run(debug=True)
