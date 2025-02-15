import csv
import os
import io
import base64
from flask import Flask, render_template_string, request, redirect, url_for, flash
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

# Define file paths
DEPARTMENTS_FILE = 'departments.csv'
SEMESTERS_FILE = 'semesters.csv'
STAFFS_FILE = 'staffs.csv'
SUBJECTS_FILE = 'subjects.csv'
ADMIN_MAPPING_FILE = 'admin_mapping.csv'
RATING_FILE = 'ratings.csv'
STUDENT_FILE = 'student.csv'  # Contains: registerno,department,semester
MAINRATING_FILE = 'mainrating.csv'  # New aggregated ratings file

# --- Helper functions ---

def read_csv_as_list(filename):
    """Return a list of values from the first column (skipping header) in the CSV file."""
    if not os.path.exists(filename):
        return []
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        return [row[0] for row in reader if row]

def load_admin_mapping(department, semester):
    """Return a list of mapping dictionaries matching the given department and semester."""
    mappings = []
    dep_norm = department.strip()
    sem_norm = semester.strip()
    if sem_norm.lower().startswith("semester"):
        sem_norm = sem_norm[len("semester"):].strip()
    if os.path.exists(ADMIN_MAPPING_FILE):
        with open(ADMIN_MAPPING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_dep = row.get('department', '').strip()
                row_sem = row.get('semester', '').strip()
                if row_sem.lower().startswith("semester"):
                    row_sem = row_sem[len("semester"):].strip()
                if row_dep == dep_norm and row_sem == sem_norm:
                    mappings.append(row)
    return mappings

def update_admin_mappings(department, semester, new_mappings):
    """
    Overwrite any existing mappings for the given department and semester
    with new_mappings. Other mappings are preserved.
    """
    dep_norm = department.strip()
    sem_norm = semester.strip()
    if sem_norm.lower().startswith("semester"):
        sem_norm = sem_norm[len("semester"):].strip()
    existing = []
    if os.path.exists(ADMIN_MAPPING_FILE):
        with open(ADMIN_MAPPING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row_dep = row.get('department', '').strip()
                row_sem = row.get('semester', '').strip()
                if row_sem.lower().startswith("semester"):
                    row_sem = row_sem[len("semester"):].strip()
                if row_dep == dep_norm and row_sem == sem_norm:
                    continue
                else:
                    existing.append(row)
    combined = existing + new_mappings
    with open(ADMIN_MAPPING_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['department', 'semester', 'staff', 'subject']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in combined:
            writer.writerow(row)

def append_ratings(rating_rows):
    """Append rating rows (list of dicts) to RATING_FILE."""
    file_exists = os.path.exists(RATING_FILE)
    with open(RATING_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['registerno', 'department', 'semester', 'staff', 'subject', 'average']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rating_rows:
            writer.writerow(row)

def get_student_info(registerno):
    """Return student info (as a dict) from STUDENT_FILE by registration number."""
    if not os.path.exists(STUDENT_FILE):
        return None
    with open(STUDENT_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('registerno') == registerno:
                return row
    return None

def has_submitted_feedback(registerno):
    """Return True if the student has already submitted feedback (exists in RATING_FILE)."""
    if not os.path.exists(RATING_FILE):
        return False
    with open(RATING_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('registerno') == registerno:
                return True
    return False

def update_mainratings():
    """
    Aggregate ratings from RATING_FILE grouped by department, semester, staff, and subject,
    and write the aggregated (overall average) data to MAINRATING_FILE.
    """
    aggregated = {}
    if os.path.exists(RATING_FILE):
        with open(RATING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dep = row.get('department', '').strip()
                sem = row.get('semester', '').strip()
                staff = row.get('staff', '').strip()
                subject = row.get('subject', '').strip()
                try:
                    rating = float(row.get('average'))
                except (ValueError, TypeError):
                    continue
                key = (dep, sem, staff, subject)
                aggregated.setdefault(key, []).append(rating)
    with open(MAINRATING_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['department', 'semester', 'staff', 'subject', 'overall_average']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for key, ratings in aggregated.items():
            dep, sem, staff, subject = key
            overall_avg = sum(ratings) / len(ratings)
            writer.writerow({
                'department': dep,
                'semester': sem,
                'staff': staff,
                'subject': subject,
                'overall_average': f"{overall_avg:.2f}"
            })

# --- Routes for Student, Admin Mapping, Feedback ---

@app.route('/', methods=['GET', 'POST'])
def student_login():
    login_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Student Login - Feedback App</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body { background: #f0f8ff; }
          header, footer { background: #007bff; color: #fff; padding: 15px; text-align: center; }
          footer a { color: #fff; text-decoration: underline; }
        </style>
      </head>
      <body class="container mt-4">
        <header><h1>VSB Engineering College</h1></header>
        <h2 class="mt-4">Student Login</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div id="flash-messages">
              {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        <form method="post">
          <div class="form-group">
            <label>Registration Number:</label>
            <input type="text" class="form-control" name="registerno" placeholder="Enter your registration number" required>
          </div>
          <button type="submit" class="btn btn-success">Proceed to Feedback</button>
        </form>
        <hr>
        <a href="{{ url_for('admin_login') }}" class="btn btn-light">Staff Page</a>
        <footer class="mt-4">These site is Created and Managed by GenrecAI. Our Site <a href="https://revolvo-ai.netlify.app" target="_blank">revolvo-ai.netlify.app</a></footer>
        <script>
          setTimeout(function() {
            var flash = document.getElementById('flash-messages');
            if (flash) { flash.style.display = 'none'; }
          }, 3000);
        </script>
      </body>
    </html>
    """
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
    return render_template_string(login_template)

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    admin_login_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Staff Login - Feedback App</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body { background: #f0f8ff; }
          header, footer { background: #007bff; color: #fff; padding: 15px; text-align: center; }
          footer a { color: #fff; text-decoration: underline; }
        </style>
      </head>
      <body class="container mt-4">
        <header><h1>Staff Login</h1></header>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div id="flash-messages">
              {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        <form method="post">
          <div class="form-group">
            <label>Password:</label>
            <input type="password" class="form-control" name="password" placeholder="Enter Staff password" required>
          </div>
          <button type="submit" class="btn btn-primary">Login</button>
        </form>
        <footer class="mt-4">
          <a href="{{ url_for('student_login') }}">Back to Student Login</a>
          <br>These site is Created and Managed by GenrecAI. Our Site <a href="https://revolvo-ai.netlify.app" target="_blank">revolvo-ai.netlify.app</a>
        </footer>
        <script>
          setTimeout(function(){
            var flash = document.getElementById('flash-messages');
            if (flash) { flash.style.display = 'none'; }
          }, 3000);
        </script>
      </body>
    </html>
    """
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'vsbec':
            return redirect(url_for('admin'))
        else:
            flash("Incorrect password.", "danger")
            return redirect(url_for('admin_login'))
    return render_template_string(admin_login_template)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    staffs = read_csv_as_list(STAFFS_FILE)
    subjects = read_csv_as_list(SUBJECTS_FILE)
    
    admin_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Staff - Feedback App</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body { background: #f0f8ff; }
          header, footer { background: #007bff; color: #fff; padding: 15px; text-align: center; }
          footer a { color: #fff; text-decoration: underline; }
        </style>
      </head>
      <body class="container mt-4">
        <header><h1>VSB Engineering College - Staff Mapping</h1></header>
        <h2 class="mt-4">Staff Page</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div id="flash-messages">
              {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        <form method="post">
          <div class="form-group">
            <label>Department:</label>
            <select class="form-control" name="department" required>
              {% for dept in departments %}
                <option value="{{ dept }}">{{ dept }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="form-group">
            <label>Semester:</label>
            <select class="form-control" name="semester" required>
              {% for sem in semesters %}
                <option value="{{ sem }}">{{ sem }}</option>
              {% endfor %}
            </select>
          </div>
          <h3>Enter Staff – Subject Mappings</h3>
          <p>You can add multiple rows. (Leave blank rows to ignore.)</p>
          <table class="table table-bordered">
            <thead class="thead-light">
              <tr>
                <th>Staff</th>
                <th>Subject</th>
              </tr>
            </thead>
            <tbody>
              {% for i in range(10) %}
              <tr>
                <td><input class="form-control" name="staff" list="staffs" placeholder="Search Staff"></td>
                <td><input class="form-control" name="subject" list="subjects" placeholder="Search Subject"></td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
          <datalist id="staffs">
            {% for s in staffs %}
              <option value="{{ s }}">
            {% endfor %}
          </datalist>
          <datalist id="subjects">
            {% for sub in subjects %}
              <option value="{{ sub }}">
            {% endfor %}
          </datalist>
          <button type="submit" class="btn btn-primary">Save Mappings</button>
        </form>
        
        <!-- New form for adding students -->
        <hr>
        <h3>Add Students</h3>
        <form id="addStudentsForm" action="/addStudents" method="POST">
          <div class="form-group">
            <label for="studentDept">Department:</label>
            <select class="form-control" name="department" id="studentDept" required>
              {% for dept in departments %}
                <option value="{{ dept }}">{{ dept }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="form-group">
            <label for="studentSem">Semester:</label>
            <select class="form-control" name="semester" id="studentSem" required>
              {% for sem in semesters %}
                <option value="{{ sem }}">{{ sem }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="form-group">
            <label for="startReg">Start Registration Number:</label>
            <input type="text" class="form-control" name="startReg" id="startReg" required>
          </div>
          <div class="form-group">
            <label for="endReg">End Registration Number:</label>
            <input type="text" class="form-control" name="endReg" id="endReg" required>
          </div>
          <button type="submit" class="btn btn-success">Add Students</button>
        </form>
        <!-- End new form -->
        
        <hr>
        <a href="{{ url_for('student_login') }}" class="btn btn-light">Go to Student Feedback Page</a>
        <footer class="mt-4">These site is Created and Managed by GenrecAI. Our Site <a href="https://revolvo-ai.netlify.app" target="_blank">revolvo-ai.netlify.app</a></footer>
        <script>
          setTimeout(function() {
            var flash = document.getElementById('flash-messages');
            if (flash) { flash.style.display = 'none'; }
          }, 3000);
        </script>
      </body>
    </html>
    """
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
        } for staff, subject in zip(staff_list, subject_list) if staff.strip() and subject.strip()]
        if not new_mappings:
            flash("Please enter at least one valid staff–subject mapping.", "danger")
        else:
            update_admin_mappings(department, semester, new_mappings)
            flash("Mapping(s) saved successfully.", "success")
            return redirect(url_for('admin'))
    return render_template_string(admin_template,
                                  departments=departments,
                                  semesters=semesters,
                                  staffs=staffs,
                                  subjects=subjects)

# New route for adding students to student.csv
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
        import csv
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
    import csv
    with open(STUDENT_FILE, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['registerno', 'department', 'semester']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in filtered_records:
            writer.writerow(row)
    
    flash(f"Students added/updated successfully ({start_num} to {end_num}).", "success")
    return redirect(url_for('admin'))

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
    questions = [
        "How is the faculty's approach?",
        "How has the faculty prepared for the classes?",
        "Does the faculty inform you about your expected competencies, course outcomes?",
        "How often does the faculty illustrate the concepts through examples and practical applications?",
        "Whether faculty covers syllabus in time?",
        "Do you agree that the faculty teaches content beyond syllabus?",
        "How does the faculty communicate?",
        "Whether faculty returns answer scripts in time and produces helpful comments?",
        "How does the faculty identify your strengths and encourage you with high level of challenges?",
        "How does the faculty counsel & encourage the students?"
    ]
    feedback_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Feedback for {{ department }} - {{ semester }}</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body { background: #f0f8ff; }
          header, footer { background: #007bff; color: #fff; padding: 15px; text-align: center; }
          .rating-table th, .rating-table td { text-align: center; vertical-align: middle; }
          .questions-box { border: 1px solid #007bff; padding: 1rem; margin-top: 1.5rem; border-radius: 5px; background: #fff; }
          .table-responsive { max-height: 60vh; overflow-y: auto; }
          select.form-control { min-width: 80px; height: 45px; font-size: 16px; color: #000; }
        </style>
      </head>
      <body class="container-fluid mt-4">
        <header><h1>VSB Engineering College</h1></header>
        <h2 class="mt-4 text-center">Feedback for {{ department }} - {{ semester }}</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div id="flash-messages">
              {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        <form method="post" id="feedbackForm">
          <div class="table-responsive">
            <table class="table table-bordered rating-table">
              <thead class="thead-light">
                <tr>
                  <th>Staff Name</th>
                  <th>Subject</th>
                  {% for q in range(1, 11) %}
                    <th>Q{{ q }}</th>
                  {% endfor %}
                  <th>Average</th>
                </tr>
              </thead>
              <tbody>
                {% for mapping in mappings %}
                  {% set idx = loop.index0 %}
                  <tr>
                    <td>{{ mapping.staff }}</td>
                    <td>{{ mapping.subject }}</td>
                    {% for q in range(1, 11) %}
                      <td>
                        <select class="form-control" id="rating-{{ idx }}-{{ q }}" 
                                name="rating-{{ idx }}-{{ q }}" required 
                                onchange="updateAverage({{ idx }})">
                          <option value="">--</option>
                          {% for i in range(1, 11) %}
                            <option value="{{ i }}">{{ i }}</option>
                          {% endfor %}
                        </select>
                      </td>
                    {% endfor %}
                    <td id="avg-{{ idx }}">0</td>
                  </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          <div class="questions-box">
            <h5>Questions</h5>
            <ol>
              {% for question in questions %}
                <li>{{ question }}</li>
              {% endfor %}
            </ol>
          </div>
          <div class="text-center mt-4">
            <button type="submit" class="btn btn-primary">Submit Feedback</button>
          </div>
        </form>
        <footer class="mt-4">
          <a href="{{ url_for('student_login') }}" style="color: #fff;">Back to Student Login</a>
          <br>These site is Created and Managed by GenrecAI. Our Site <a href="https://revolvo-ai.netlify.app" target="_blank" style="color: #fff;">revolvo-ai.netlify.app</a>
        </footer>
        <script>
          setTimeout(function() {
            var flash = document.getElementById('flash-messages');
            if (flash) { flash.style.display = 'none'; }
          }, 3000);
          function updateAverage(idx) {
            var total = 0, count = 0;
            for (var q = 1; q <= 10; q++) {
              var selectElem = document.getElementById('rating-' + idx + '-' + q);
              var val = parseFloat(selectElem.value);
              if (!isNaN(val)) { total += val; count++; }
            }
            var avgElem = document.getElementById('avg-' + idx);
            avgElem.textContent = (count === 10) ? (total / count).toFixed(2) : 'N/A';
          }
        </script>
      </body>
    </html>
    """
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
            return redirect(url_for('feedback', department=department, semester=semester, registerno=registerno))
        else:
            append_ratings(rating_rows)
            flash("Feedback submitted successfully. Thank you!", "success")
            return redirect(url_for('student_login'))
    return render_template_string(feedback_template,
                                  department=department,
                                  semester=semester,
                                  mappings=mappings,
                                  questions=questions)

# --- New Routes for HOD/VP Report Generation ---

@app.route('/hod', methods=['GET', 'POST'])
def hod_login():
    hod_login_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>HOD Login - Report</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body { background: #f0f8ff; }
          header, footer { background: #007bff; color: #fff; padding: 15px; text-align: center; }
          footer a { color: #fff; text-decoration: underline; }
        </style>
      </head>
      <body class="container mt-4">
        <header><h1>HOD Login</h1></header>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div id="flash-messages">
              {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        <form method="post">
          <div class="form-group">
            <label>Username:</label>
            <input type="text" class="form-control" name="username" placeholder="Enter username" required>
          </div>
          <div class="form-group">
            <label>Password:</label>
            <input type="password" class="form-control" name="password" placeholder="Enter password" required>
          </div>
          <button type="submit" class="btn btn-primary">Login</button>
        </form>
        <footer class="mt-4">
          <a href="{{ url_for('student_login') }}">Back to Student Login</a>
          <br>These site is Created and Managed by GenrecAI. Our Site <a href="https://revolvo-ai.netlify.app" target="_blank">revolvo-ai.netlify.app</a>
        </footer>
        <script>
          setTimeout(function(){
            var flash = document.getElementById('flash-messages');
            if (flash) { flash.style.display = 'none'; }
          }, 3000);
        </script>
      </body>
    </html>
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            return redirect(url_for('hod_select'))
        else:
            flash("Incorrect credentials.", "danger")
            return redirect(url_for('hod_login'))
    return render_template_string(hod_login_template)

@app.route('/hod/select', methods=['GET', 'POST'])
def hod_select():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    hod_select_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Select Report - HOD</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body { background: #f0f8ff; }
          header, footer { background: #007bff; color: #fff; padding: 15px; text-align: center; }
          footer a { color: #fff; text-decoration: underline; }
        </style>
      </head>
      <body class="container mt-4">
        <header><h1>Select Department & Semester</h1></header>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div id="flash-messages">
              {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
              {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        <form method="post">
          <div class="form-group">
            <label>Department:</label>
            <select class="form-control" name="department" required>
              <option value="">--Select Department--</option>
              {% for dept in departments %}
                <option value="{{ dept }}">{{ dept }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="form-group">
            <label>Semester:</label>
            <select class="form-control" name="semester" required>
              <option value="">--Select Semester--</option>
              {% for sem in semesters %}
                <option value="{{ sem }}">{{ sem }}</option>
              {% endfor %}
            </select>
          </div>
          <button type="submit" name="action" value="generate" class="btn btn-success">Generate Report</button>
          <button type="submit" name="action" value="download" class="btn btn-info">Download Report</button>
        </form>
        <footer class="mt-4">
          <a href="{{ url_for('hod_login') }}">Back to HOD Login</a>
          <br>These site is Created and Managed by GenrecAI. Our Site <a href="https://revolvo-ai.netlify.app" target="_blank">revolvo-ai.netlify.app</a>
        </footer>
        <script>
          setTimeout(function(){
            var flash = document.getElementById('flash-messages');
            if (flash) { flash.style.display = 'none'; }
          }, 3000);
        </script>
      </body>
    </html>
    """
    if request.method == 'POST':
        department = request.form.get('department')
        semester = request.form.get('semester')
        action = request.form.get('action')
        if not department or not semester:
            flash("Please select both department and semester.", "danger")
        else:
            if action == 'download':
                return redirect(url_for('download_report', department=department, semester=semester))
            else:
                return redirect(url_for('hod_report', department=department, semester=semester))
    return render_template_string(hod_select_template, departments=departments, semesters=semesters)

# ... (Keep all previous code the same until the hod_report function)

@app.route('/hod/report')
def hod_report():
    department = request.args.get('department')
    semester = request.args.get('semester')
    if not department or not semester:
        flash("Missing department or semester selection.", "danger")
        return redirect(url_for('hod_select'))
    
    normalized_input_semester = semester.strip()
    if normalized_input_semester.lower().startswith("semester"):
        normalized_input_semester = normalized_input_semester[len("semester"):].strip()
    
    update_mainratings()
    data = {}
    if os.path.exists(MAINRATING_FILE):
        with open(MAINRATING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dep = row.get('department', '').strip()
                sem = row.get('semester', '').strip()
                if sem.lower().startswith("semester"):
                    sem = sem[len("semester"):].strip()
                if dep == department.strip() and sem == normalized_input_semester:
                    key = f"{row.get('staff').strip()} ({row.get('subject').strip()})"
                    try:
                        overall = float(row.get('overall_average'))
                    except (ValueError, TypeError):
                        continue
                    data[key] = overall
    
    if not data:
        report_message = f"<h2>No rating data found for {department} - {semester}.</h2>"
        return report_message
    
    labels = list(data.keys())
    # Wrap long labels (staff name and subject)
    import textwrap
    labels = [textwrap.fill(label, width=15) for label in labels]
    averages_list = list(data.values())
    
    # Create improved horizontal bar chart
    if 'seaborn' in plt.style.available:
        plt.style.use('seaborn')
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Create color gradient based on rating values
    colors = plt.cm.viridis([x/10 for x in averages_list])
    
    bars = ax.barh(labels, averages_list, color=colors, edgecolor='black')
    
    # Customize appearance
    ax.set_xlabel('Average Rating', fontsize=12, fontweight='bold')
    ax.set_ylabel('Staff (Subject)', fontsize=12, fontweight='bold')
    ax.set_title(f'Average Ratings - {department} - Semester {normalized_input_semester}\n',
                 fontsize=16, fontweight='bold', pad=20)
    
    # Set x-axis limits and ticks
    ax.set_xlim(0, 10)
    ax.set_xticks(range(0, 11))
    ax.xaxis.set_tick_params(labelsize=10)
    ax.yaxis.set_tick_params(labelsize=10)
    
    # Add grid
    ax.grid(True, axis='x', linestyle='--', alpha=0.7)
    
    # Add value labels on bars
    for bar in bars:
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2,
                f'{width:.2f}',
                va='center', ha='left', fontsize=10)
    
    plt.tight_layout()
    
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    
    overall_avg = f"{sum(averages_list)/len(averages_list):.2f}" if averages_list else "N/A"
    
    report_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Report for {{ department }} - {{ semester }}</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body { background: #f8f9fa; margin: 0; padding: 20px 0; }
          .header-container { max-width: 1200px; margin: 0 auto; }
          .graph-container { max-width: 1200px; margin: 20px auto; background: white; padding: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
          .report-title { color: #2c3e50; text-align: center; margin-bottom: 30px; }
          .overall-average { 
              text-align: center; 
              font-size: 1.4rem; 
              margin: 20px 0;
              padding: 10px;
              background: #007bff;
              color: white;
              border-radius: 5px;
              max-width: 300px;
              margin-left: auto;
              margin-right: auto;
          }
          .download-btn {
              text-align: center;
              margin: 20px 0;
          }
          footer {
              text-align: center;
              margin-top: 30px;
              padding: 20px;
              color: #6c757d;
          }
        </style>
      </head>
      <body>
        <div class="header-container">
          <h1 class="report-title">Faculty Performance Report</h1>
          <div class="overall-average">
            Overall Department Average: {{ averages }}
          </div>
        </div>
        
        <div class="graph-container">
          <img src="data:image/png;base64,{{ graph_url }}" alt="Report Graph" class="img-fluid">
        </div>
        
        <div class="download-btn">
          <a href="{{ url_for('download_report', department=department, semester=semester) }}" class="btn btn-primary btn-lg">
            Download Full Report Data
          </a>
        </div>
        
        <footer>
          <p>Report generated on {{ date }} | These site is Created and Managed by GenrecAI</p>
          <a href="{{ url_for('hod_select') }}" class="btn btn-outline-secondary">Back to Report Selection</a>
        </footer>
      </body>
    </html>
    """
    
    from datetime import datetime
    return render_template_string(report_template, 
                                 department=department,
                                 semester=semester,
                                 graph_url=graph_url,
                                 averages=overall_avg,
                                 date=datetime.now().strftime("%Y-%m-%d %H:%M"))

# ... (Keep the rest of the code the same)
@app.route('/hod/download_report')
def download_report():
    department = request.args.get('department')
    semester = request.args.get('semester')
    if not department or not semester:
        flash("Missing department or semester selection.", "danger")
        return redirect(url_for('hod_select'))
    
    normalized_input_semester = semester.strip()
    if normalized_input_semester.lower().startswith("semester"):
        normalized_input_semester = normalized_input_semester[len("semester"):].strip()
    
    update_mainratings()
    
    data = {}
    if os.path.exists(MAINRATING_FILE):
        with open(MAINRATING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dep = row.get('department', '').strip()
                sem = row.get('semester', '').strip()
                if sem.lower().startswith("semester"):
                    sem = sem[len("semester"):].strip()
                if dep == department.strip() and sem == normalized_input_semester:
                    key = f"{row.get('staff').strip()} ({row.get('subject').strip()})"
                    try:
                        overall = float(row.get('overall_average'))
                    except (ValueError, TypeError):
                        continue
                    data[key] = overall
    if not data:
        flash("No rating data found for the selected department and semester.", "danger")
        return redirect(url_for('hod_select'))
    
    labels = list(data.keys())
    import textwrap
    labels = [textwrap.fill(label, width=15) for label in labels]
    averages_list = list(data.values())
    
    if 'seaborn' in plt.style.available:
        plt.style.use('seaborn')
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
    
    # Save the graph to a BytesIO stream and return it as a downloadable PNG image
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', dpi=100)
    img.seek(0)
    plt.close()
    
    from flask import send_file
    safe_department = department.replace(' ', '_').replace('/', '_')
    safe_semester = semester.replace(' ', '_').replace('/', '_')
    filename = f"report_{safe_department}_{safe_semester}.png"
    return send_file(img, mimetype='image/png', as_attachment=True, download_name=filename)

if __name__ == '__main__':
    # Create CSV files if they don't exist
    required_files = {
        DEPARTMENTS_FILE: ['department'],
        SEMESTERS_FILE: ['semester'],
        STAFFS_FILE: ['staff_name'],
        SUBJECTS_FILE: ['subject_name'],
        ADMIN_MAPPING_FILE: ['department', 'semester', 'staff', 'subject'],
        RATING_FILE: ['registerno', 'department', 'semester', 'staff', 'subject', 'average'],
        STUDENT_FILE: ['registerno', 'department', 'semester']
    }
    for file, headers in required_files.items():
        if not os.path.exists(file):
            with open(file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
       
    app.run(debug=True)
