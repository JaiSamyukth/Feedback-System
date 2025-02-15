from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from utils import read_csv_as_list, update_mainratings, normalize_semester
from config import (DEPARTMENTS_FILE, SEMESTERS_FILE, MAINRATING_FILE, 
                   RATING_FILE, STUDENT_FILE, REQUIRED_FILES)
import os
import csv
import io
import base64
import matplotlib.pyplot as plt
from datetime import datetime
import textwrap
import shutil

hod_bp = Blueprint('hod', __name__)

def create_empty_csv(file_path, headers):
    """Create a new CSV file with only headers."""
    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

def safe_move_file(src, dst):
    """Move file if it exists, create empty one if it doesn't."""
    if os.path.exists(src):
        shutil.copy2(src, dst)  # Copy with metadata

@hod_bp.route('/hod/archive', methods=['POST'])
def archive_data():
    department = request.form.get('department')
    semester = request.form.get('semester')
    
    if not department or not semester:
        flash("Missing department or semester information.", "danger")
        return redirect(url_for('hod.hod_select'))

    try:
        # Create history directory if it doesn't exist
        if not os.path.exists('history'):
            os.makedirs('history')

        # Create timestamped directory
        timestamp = datetime.now().strftime("%Y%m%d--%H%M%S")
        archive_dir = os.path.join('history', f"{timestamp}-{department}-{semester}")
        os.makedirs(archive_dir)

        # Move files to archive
        files_to_archive = [MAINRATING_FILE, RATING_FILE, STUDENT_FILE]
        for file in files_to_archive:
            if os.path.exists(file):
                archive_path = os.path.join(archive_dir, os.path.basename(file))
                safe_move_file(file, archive_path)

        # Reset current files
        create_empty_csv(RATING_FILE, REQUIRED_FILES[RATING_FILE])
        create_empty_csv(STUDENT_FILE, REQUIRED_FILES[STUDENT_FILE])
        if os.path.exists(MAINRATING_FILE):
            os.remove(MAINRATING_FILE)  # This will be regenerated when needed

        flash("Data successfully archived and system reset.", "success")
        return redirect(url_for('hod.hod_select'))

    except Exception as e:
        flash(f"Error during archival process: {str(e)}", "danger")
        return redirect(url_for('hod.hod_report', department=department, semester=semester))

@hod_bp.route('/hod', methods=['GET', 'POST'])
def hod_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            return redirect(url_for('hod.hod_select'))
        else:
            flash("Incorrect credentials.", "danger")
            return redirect(url_for('hod.hod_login'))
    return render_template('hod_login.html')

@hod_bp.route('/hod/select', methods=['GET', 'POST'])
def hod_select():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    
    if request.method == 'POST':
        department = request.form.get('department')
        semester = request.form.get('semester')
        action = request.form.get('action')
        
        if not department or not semester:
            flash("Please select both department and semester.", "danger")
        else:
            if action == 'download':
                return redirect(url_for('hod.download_report', 
                                      department=department, semester=semester))
            else:
                return redirect(url_for('hod.hod_report', 
                                      department=department, semester=semester))
    
    return render_template('hod_select.html', 
                         departments=departments, semesters=semesters)

@hod_bp.route('/hod/report')
def hod_report():
    department = request.args.get('department')
    semester = request.args.get('semester')
    
    if not department or not semester:
        flash("Missing department or semester selection.", "danger")
        return redirect(url_for('hod.hod_select'))

    normalized_input_semester = normalize_semester(semester)
    update_mainratings()
    
    data = {}
    if os.path.exists(MAINRATING_FILE):
        with open(MAINRATING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dep = row.get('department', '').strip()
                sem = normalize_semester(row.get('semester', ''))
                if dep == department.strip() and sem == normalized_input_semester:
                    key = f"{row.get('staff').strip()} ({row.get('subject').strip()})"
                    try:
                        overall = float(row.get('overall_average'))
                        data[key] = overall
                    except (ValueError, TypeError):
                        continue

    if not data:
        return f"<h2>No rating data found for {department} - {semester}.</h2>"

    labels = list(data.keys())
    labels = [textwrap.fill(label, width=15) for label in labels]
    averages_list = list(data.values())

    plt.switch_backend('Agg')  # Use non-interactive backend
    
    fig, ax = plt.subplots(figsize=(14, 8))
    colors = plt.cm.viridis([x/10 for x in averages_list])
    bars = ax.barh(labels, averages_list, color=colors, edgecolor='black')

    ax.set_xlabel('Average Rating', fontsize=12, fontweight='bold')
    ax.set_ylabel('Staff (Subject)', fontsize=12, fontweight='bold')
    ax.set_title(f'Average Ratings - {department} - Semester {normalized_input_semester}\n',
                fontsize=16, fontweight='bold', pad=20)

    ax.set_xlim(0, 10)
    ax.set_xticks(range(0, 11))
    ax.xaxis.set_tick_params(labelsize=10)
    ax.yaxis.set_tick_params(labelsize=10)
    ax.grid(True, axis='x', linestyle='--', alpha=0.7)

    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                f'{width:.2f}', va='center', ha='left', fontsize=10)

    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()

    overall_avg = f"{sum(averages_list)/len(averages_list):.2f}" if averages_list else "N/A"

    return render_template('hod_report.html',
                         department=department,
                         semester=semester,
                         graph_url=graph_url,
                         averages=overall_avg,
                         date=datetime.now().strftime("%Y-%m-%d %H:%M"))

@hod_bp.route('/hod/download_report')
def download_report():
    department = request.args.get('department')
    semester = request.args.get('semester')
    
    if not department or not semester:
        flash("Missing department or semester selection.", "danger")
        return redirect(url_for('hod.hod_select'))

    normalized_input_semester = normalize_semester(semester)
    update_mainratings()
    
    # Create CSV file in memory
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Staff Name', 'Subject', 'Average Rating'])
    
    if os.path.exists(MAINRATING_FILE):
        with open(MAINRATING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dep = row.get('department', '').strip()
                sem = normalize_semester(row.get('semester', ''))
                if dep == department.strip() and sem == normalized_input_semester:
                    staff = row.get('staff', '').strip()
                    subject = row.get('subject', '').strip()
                    avg = row.get('overall_average', '0.00').strip()
                    writer.writerow([staff, subject, avg])

    # Prepare the CSV file for download
    output.seek(0)
    safe_department = department.replace(' ', '_').replace('/', '_')
    safe_semester = semester.replace(' ', '_').replace('/', '_')
    filename = f"feedback_report_{safe_department}_{safe_semester}.csv"
    
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )