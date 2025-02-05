import csv
import os
from flask import Flask, render_template_string, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

# Define file paths (adjust the paths as needed)
DEPARTMENTS_FILE = 'departments.csv'
SEMESTERS_FILE = 'semesters.csv'
STAFFS_FILE = 'staffs.csv'
SUBJECTS_FILE = 'subjects.csv'
ADMIN_MAPPING_FILE = 'admin_mapping.csv'
RATING_FILE = 'rating.csv'

# --- Helper functions to read CSV files ---
def read_csv_as_list(filename):
    """Return a list of values from the first column (skipping header) in the CSV file."""
    items = []
    if os.path.exists(filename):
        with open(filename, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if row:
                    items.append(row[0])
    return items

def load_admin_mapping(department, semester):
    """Return list of mappings (each a dict) matching the given department and semester."""
    mappings = []
    if os.path.exists(ADMIN_MAPPING_FILE):
        with open(ADMIN_MAPPING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('department') == department and row.get('semester') == semester:
                    mappings.append(row)
    return mappings

def append_admin_mappings(mappings):
    """
    Append a list of dictionaries (with keys: department, semester, staff, subject)
    to the admin_mapping.csv file. Write header if the file doesn't exist.
    """
    file_exists = os.path.exists(ADMIN_MAPPING_FILE)
    with open(ADMIN_MAPPING_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['department', 'semester', 'staff', 'subject']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for m in mappings:
            writer.writerow(m)

def append_ratings(rating_rows):
    """
    Append a list of dictionaries (with keys: department, semester, staff, subject, average)
    to the rating.csv file. Write header if the file doesn't exist.
    """
    file_exists = os.path.exists(RATING_FILE)
    with open(RATING_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['department', 'semester', 'staff', 'subject', 'average']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rating_rows:
            writer.writerow(row)

# --- Routes ---

# 1. Admin Page: To add staff–subject mappings per department/semester.
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    staffs = read_csv_as_list(STAFFS_FILE)
    subjects = read_csv_as_list(SUBJECTS_FILE)
    
    if request.method == 'POST':
        # The admin form sends:
        #   department, semester,
        #   staff[] and subject[] (lists of values)
        department = request.form.get('department')
        semester = request.form.get('semester')
        staff_list = request.form.getlist('staff')
        subject_list = request.form.getlist('subject')
        
        # Validate at least one non-empty mapping
        mappings = []
        for staff, subject in zip(staff_list, subject_list):
            if staff.strip() and subject.strip():
                mappings.append({
                    'department': department,
                    'semester': semester,
                    'staff': staff,
                    'subject': subject
                })
        if not mappings:
            flash("Please enter at least one valid staff–subject mapping.", "danger")
        else:
            append_admin_mappings(mappings)
            flash("Mapping(s) saved successfully.", "success")
            return redirect(url_for('admin'))
    
    admin_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Admin - Feedback App</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
      </head>
      <body class="container mt-4">
        <h1>Admin Page</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div>
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
            <thead>
              <tr>
                <th>Staff</th>
                <th>Subject</th>
              </tr>
            </thead>
            <tbody>
              {% for i in range(5) %}
              <tr>
                <td>
                  <select class="form-control" name="staff">
                    <option value="">--Select Staff--</option>
                    {% for s in staffs %}
                      <option value="{{ s }}">{{ s }}</option>
                    {% endfor %}
                  </select>
                </td>
                <td>
                  <select class="form-control" name="subject">
                    <option value="">--Select Subject--</option>
                    {% for sub in subjects %}
                      <option value="{{ sub }}">{{ sub }}</option>
                    {% endfor %}
                  </select>
                </td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
          <button type="submit" class="btn btn-primary">Save Mappings</button>
        </form>
        <hr>
        <a href="{{ url_for('select_department_semester') }}">Go to Student Feedback Page</a>
      </body>
    </html>
    """
    return render_template_string(admin_template,
                                  departments=departments,
                                  semesters=semesters,
                                  staffs=staffs,
                                  subjects=subjects)

# 2. First Page for Students: Select Department and Semester
@app.route('/', methods=['GET', 'POST'])
def select_department_semester():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    
    if request.method == 'POST':
        department = request.form.get('department')
        semester = request.form.get('semester')
        if not department or not semester:
            flash("Please select both department and semester.", "danger")
        else:
            return redirect(url_for('feedback', department=department, semester=semester))
    
    select_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Student: Select Department and Semester</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
      </head>
      <body class="container mt-4">
        <h1>Provide Your Feedback</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div>
            {% for category, message in messages %}
              <div class="alert alert-danger">{{ message }}</div>
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
          <button type="submit" class="btn btn-success">Proceed to Feedback</button>
        </form>
        <hr>
        <a href="{{ url_for('admin') }}">Admin Page</a>
      </body>
    </html>
    """
    return render_template_string(select_template, departments=departments, semesters=semesters)

# 3. Student Feedback Page:
@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    department = request.args.get('department')
    semester = request.args.get('semester')
    if not department or not semester:
        flash("Department and Semester not specified.", "danger")
        return redirect(url_for('select_department_semester'))
    
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
    
    if request.method == 'POST':
        rating_rows = []
        error_flag = False
        # Process each mapping row
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
                'department': department,
                'semester': semester,
                'staff': mapping['staff'],
                'subject': mapping['subject'],
                'average': f"{average:.2f}"
            })
        if error_flag:
            return redirect(url_for('feedback', department=department, semester=semester))
        else:
            append_ratings(rating_rows)
            flash("Feedback submitted successfully. Thank you!", "success")
            return redirect(url_for('select_department_semester'))
    
    feedback_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Feedback for {{ department }} - {{ semester }}</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <script>
          // Compute the average rating for each staff row dynamically.
          function computeAverage(idx) {
            let total = 0;
            let count = 0;
            for (let q = 1; q <= 10; q++) {
              let input = document.getElementById('rating-' + idx + '-' + q);
              let val = parseFloat(input.value);
              if (!isNaN(val)) {
                total += val;
                count++;
              }
            }
            let avgCell = document.getElementById('avg-' + idx);
            if(count === 10) {
                avgCell.innerText = (total / count).toFixed(2);
            } else {
                avgCell.innerText = "N/A";
            }
          }
          function attachListeners() {
            {% for idx in range(mappings|length) %}
              for (let q = 1; q <= 10; q++) {
                document.getElementById('rating-{{ idx }}-' + q).addEventListener('change', function() {
                  computeAverage({{ idx }});
                });
              }
            {% endfor %}
          }
          window.onload = attachListeners;
        </script>
      </head>
      <body class="container mt-4">
        <h1>Feedback for {{ department }} - {{ semester }}</h1>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div>
            {% for category, message in messages %}
              <div class="alert alert-{{ 'danger' if category == 'danger' else 'success' }}">{{ message }}</div>
            {% endfor %}
            </div>
          {% endif %}
        {% endwith %}
        <form method="post">
          <table class="table table-bordered">
            <thead>
              <tr>
                <th>Staff</th>
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
                      <select class="form-control" id="rating-{{ idx }}-{{ q }}" name="rating-{{ idx }}-{{ q }}" required>
                        <option value="">--</option>
                        {% for i in range(1, 11) %}
                          <option value="{{ i }}">{{ i }}</option>
                        {% endfor %}
                      </select>
                    </td>
                  {% endfor %}
                  <td id="avg-{{ idx }}">N/A</td>
                </tr>
                <tr>
                  <td colspan="{{ 2 + 10 + 1 }}">
                    <ol>
                      {% for question in questions %}
                        <li>{{ question }}</li>
                      {% endfor %}
                    </ol>
                  </td>
                </tr>
              {% endfor %}
            </tbody>
          </table>
          <button type="submit" class="btn btn-primary">Submit Feedback</button>
        </form>
        <hr>
        <a href="{{ url_for('select_department_semester') }}">Back to Department Selection</a>
      </body>
    </html>
    """
    return render_template_string(feedback_template,
                                  department=department,
                                  semester=semester,
                                  mappings=mappings,
                                  questions=questions)

if __name__ == '__main__':
    # Run in debug mode for development
    app.run(debug=True)
