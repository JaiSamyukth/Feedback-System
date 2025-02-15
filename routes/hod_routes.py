from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, make_response
from utils import read_csv_as_list, update_mainratings, normalize_semester
from config import (DEPARTMENTS_FILE, SEMESTERS_FILE, MAINRATING_FILE,
                   RATING_FILE, STUDENT_FILE, REQUIRED_FILES, ADMIN_MAPPING_FILE)
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

@hod_bp.route('/hod/download_graph')
def download_graph():
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
                    staff_name = row.get('staff').strip()
                    subject_name = row.get('subject').strip()
                    key = f"{staff_name} ({subject_name})"
                    try:
                        overall = float(row.get('overall_average'))
                        data[key] = overall
                    except (ValueError, TypeError):
                        continue

    if not data:
        flash("No data available to generate graph.", "danger")
        return redirect(url_for('hod.hod_report', department=department, semester=semester))

    # Prepare data for graph
    labels = [textwrap.fill(key, width=15) for key in data.keys()]
    averages_list = list(data.values())

    plt.switch_backend('Agg')
    
    # Create figure with high DPI for better quality
    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
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

    # Save to BytesIO with high DPI
    img_io = io.BytesIO()
    plt.savefig(img_io, format='png', bbox_inches='tight', dpi=300)
    img_io.seek(0)
    plt.close()

    filename = f"ratings_graph_{department.replace(' ', '_')}_{semester.replace(' ', '_')}.png"
    
    return send_file(
        img_io,
        mimetype='image/png',
        as_attachment=True,
        download_name=filename
    )

@hod_bp.route('/hod/select', methods=['GET', 'POST'])
def hod_select():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Handle actions that don't need department/semester
        if action == 'download':
            # Update mainrating.csv with all data before downloading
            update_mainratings()
            
            if not os.path.exists(MAINRATING_FILE):
                flash("No report data available.", "danger")
                return redirect(url_for('hod.hod_select'))
            
            return send_file(
                MAINRATING_FILE,
                mimetype='text/csv',
                as_attachment=True,
                download_name='mainrating.csv'
            )
        elif action == 'archive':
            try:
                # Ensure history directory exists
                if not os.path.exists('history'):
                    os.makedirs('history')

                # Create timestamped directory
                timestamp = datetime.now().strftime("%d-%b-%Y--%H-%M-%S")
                archive_dir = os.path.join('history', timestamp)
                
                # Create directory
                if not os.path.exists(archive_dir):
                    os.makedirs(archive_dir)
                
                # List of files to handle with their headers
                files_to_handle = {
                    RATING_FILE: REQUIRED_FILES[RATING_FILE],
                    STUDENT_FILE: REQUIRED_FILES[STUDENT_FILE],
                    ADMIN_MAPPING_FILE: ['department', 'semester', 'staff', 'subject'],
                    MAINRATING_FILE: None  # No header needed as file will be regenerated
                }

                # Archive and reset each file
                for file, headers in files_to_handle.items():
                    if os.path.exists(file):
                        # Copy to archive
                        archive_path = os.path.join(archive_dir, os.path.basename(file))
                        safe_move_file(file, archive_path)
                        
                        # Reset file with headers (except mainrating.csv)
                        if headers is not None:
                            create_empty_csv(file, headers)
                        elif file == MAINRATING_FILE:
                            # Remove mainrating.csv as it will be regenerated
                            os.remove(file)

                flash("Data successfully archived and system reset.", "success")
                return redirect(url_for('hod.hod_select'))

            except Exception as e:
                flash(f"Error during archival process: {str(e)}", "danger")
                return redirect(url_for('hod.hod_select'))
        
        # For report generation, we need department and semester
        department = request.form.get('department')
        semester = request.form.get('semester')
        
        if not department or not semester:
            flash("Please select both department and semester.", "danger")
            return redirect(url_for('hod.hod_select'))
        
        # Generate report
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
                    staff_name = row.get('staff').strip()
                    subject_name = row.get('subject').strip()
                    key = f"{staff_name} ({subject_name})"
                    
                    try:
                        overall = float(row.get('overall_average'))
                        data[key] = {
                            'staff': staff_name,
                            'subject': subject_name,
                            'overall_average': row.get('overall_average'),
                            'overall_float': overall
                        }
                        # Add individual question averages
                        for i in range(1, 11):
                            data[key][f'q{i}_avg'] = row.get(f'q{i}_avg', '0.00')
                    except (ValueError, TypeError):
                        continue

    if not data:
        return f"<h2>No rating data found for {department} - {semester}.</h2>"

    # Prepare data for graph
    labels = [textwrap.fill(key, width=15) for key in data.keys()]
    averages_list = [item['overall_float'] for item in data.values()]

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

    # Convert data dict values to list for template
    detailed_ratings = list(data.values())
    
    return render_template('hod_report.html',
                         department=department,
                         semester=semester,
                         graph_url=graph_url,
                         averages=overall_avg,
                         date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                         detailed_ratings=detailed_ratings)