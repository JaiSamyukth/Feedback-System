from flask import Blueprint, render_template, request, redirect, url_for, flash
from utils import read_csv_as_list, update_admin_mappings
from config import DEPARTMENTS_FILE, SEMESTERS_FILE, STAFFS_FILE, SUBJECTS_FILE

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'vsbec':
            return redirect(url_for('admin.admin'))
        else:
            flash("Incorrect password.", "danger")
            return redirect(url_for('admin.admin_login'))
    return render_template('admin_login.html')

@admin_bp.route('/admin', methods=['GET', 'POST'])
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
            return redirect(url_for('admin.admin'))

    return render_template('admin_mapping.html',
                         departments=departments,
                         semesters=semesters,
                         staffs=staffs,
                         subjects=subjects)