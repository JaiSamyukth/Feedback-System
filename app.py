import csv
import os
from flask import Flask, render_template_string, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

# Define file paths
DEPARTMENTS_FILE = 'departments.csv'
SEMESTERS_FILE = 'semesters.csv'
STAFFS_FILE = 'staffs.csv'
SUBJECTS_FILE = 'subjects.csv'
ADMIN_MAPPING_FILE = 'admin_mapping.csv'
RATING_FILE = 'rating.csv'

# --- Helper functions ---
def read_csv_as_list(filename):
    """Return a list of values from the first column (skipping header) in the CSV file."""
    if not os.path.exists(filename):
        return []
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        return [row[0] for row in reader if row]

def load_admin_mapping(department, semester):
    """Return list of mapping dictionaries matching the given department and semester."""
    mappings = []
    if os.path.exists(ADMIN_MAPPING_FILE):
        with open(ADMIN_MAPPING_FILE, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('department') == department and row.get('semester') == semester:
                    mappings.append(row)
    return mappings

def append_admin_mappings(mappings):
    """Append mappings (list of dicts) to ADMIN_MAPPING_FILE."""
    file_exists = os.path.exists(ADMIN_MAPPING_FILE)
    with open(ADMIN_MAPPING_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['department', 'semester', 'staff', 'subject']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for m in mappings:
            writer.writerow(m)

def append_ratings(rating_rows):
    """Append rating rows (list of dicts) to RATING_FILE."""
    file_exists = os.path.exists(RATING_FILE)
    with open(RATING_FILE, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['department', 'semester', 'staff', 'subject', 'average']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rating_rows:
            writer.writerow(row)

# --- Routes ---
@app.route('/', methods=['GET', 'POST'])
def select_department_semester():
    departments = read_csv_as_list(DEPARTMENTS_FILE)
    semesters = read_csv_as_list(SEMESTERS_FILE)
    
    select_template = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <title>Student: Select Department and Semester</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body {
            background: #f0f8ff;
          }
          header, footer {
            background: #007bff;
            color: #fff;
            padding: 15px;
            text-align: center;
          }
          footer a { color: #fff; text-decoration: underline; }
        </style>
      </head>
      <body class="container mt-4">
        <header>
          <h1>VSB Engineering College</h1>
        </header>
        <h2 class="mt-4">Provide Your Feedback</h2>
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
        <a href="{{ url_for('admin') }}" class="btn btn-light">Staff Page</a>
        <footer class="mt-4">
          This site is created and managed by GenrecAI. Visit our website 
          <a href="https://revolvo-ai.netlify.app" target="_blank">revolvo-ai.netlify.app</a>
        </footer>
      </body>
    </html>
    """
    if request.method == 'POST':
        department = request.form.get('department')
        semester = request.form.get('semester')
        if not department or not semester:
            flash("Please select both department and semester.", "danger")
        else:
            return redirect(url_for('feedback', department=department, semester=semester))
    
    return render_template_string(select_template, departments=departments, semesters=semesters)

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
        <title>Admin - Feedback App</title>
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
        <style>
          body {
            background: #f0f8ff;
          }
          header, footer {
            background: #007bff;
            color: #fff;
            padding: 15px;
            text-align: center;
          }
          footer a { color: #fff; text-decoration: underline; }
        </style>
      </head>
      <body class="container mt-4">
        <header>
          <h1>VSB Engineering College</h1>
        </header>
        <h2 class="mt-4">Admin Page</h2>
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
            <thead class="thead-light">
              <tr>
                <th>Staff</th>
                <th>Subject</th>
              </tr>
            </thead>
            <tbody>
              {% for i in range(10) %}
              <tr>
                <td>
                  <input class="form-control" name="staff" list="staffs" placeholder="Search Staff">
                </td>
                <td>
                  <input class="form-control" name="subject" list="subjects" placeholder="Search Subject">
                </td>
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
        <hr>
        <a href="{{ url_for('select_department_semester') }}" class="btn btn-light">Go to Student Feedback Page</a>
        <footer class="mt-4">
          This site is created and managed by GenrecAI. 
          Visit our website <a href="https://revolvo-ai.netlify.app" target="_blank">revolvo-ai.netlify.app</a>
        </footer>
      </body>
    </html>
    """
    
    if request.method == 'POST':
        department = request.form.get('department')
        semester = request.form.get('semester')
        staff_list = request.form.getlist('staff')
        subject_list = request.form.getlist('subject')
        
        mappings = [{
            'department': department,
            'semester': semester,
            'staff': staff.strip(),
            'subject': subject.strip()
        } for staff, subject in zip(staff_list, subject_list) if staff.strip() and subject.strip()]
        
        if not mappings:
            flash("Please enter at least one valid staff–subject mapping.", "danger")
        else:
            append_admin_mappings(mappings)
            flash("Mapping(s) saved successfully.", "success")
            return redirect(url_for('admin'))
    
    return render_template_string(admin_template,
                                  departments=departments,
                                  semesters=semesters,
                                  staffs=staffs,
                                  subjects=subjects)

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
    
    # Common questions for all staff
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
          body {
            background: #f0f8ff;
          }
          header, footer {
            background: #007bff;
            color: #fff;
            padding: 15px;
            text-align: center;
          }
          .rating-table th, .rating-table td {
            text-align: center;
            vertical-align: middle;
          }
          .questions-box {
            border: 1px solid #007bff;
            padding: 1rem;
            margin-top: 1.5rem;
            border-radius: 5px;
            background: #fff;
          }
          .table-responsive {
            max-height: 60vh;
            overflow-y: auto;
          }
          /* Increase select box size and ensure text is visible */
          select.form-control {
            min-width: 80px;
            height: 45px;
            font-size: 16px;
            color: #000;
          }
          /* Use full width container to fill left/right space */
          .full-width-container {
            width: 100%;
            padding: 0 15px;
          }
        </style>
      </head>
      <body class="full-width-container mt-4">
        <header>
          <h1>VSB Engineering College</h1>
        </header>
        <h2 class="mt-4 text-center">Feedback for {{ department }} - {{ semester }}</h2>
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            <div>
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
          
          <!-- Common Questions Box -->
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
          <a href="{{ url_for('select_department_semester') }}" style="color: #fff;">Back to Department Selection</a>
          <p>This site is created and managed by GenrecAI.
          Visit our website <a href="https://revolvo-ai.netlify.app" target="_blank" style="color: #fff; text-decoration: underline;">revolvo-ai.netlify.app</a></p>
        </footer>
        <script>
          function updateAverage(idx) {
            var total = 0;
            var count = 0;
            for (var q = 1; q <= 10; q++) {
              var selectElem = document.getElementById('rating-' + idx + '-' + q);
              var val = parseFloat(selectElem.value);
              if (!isNaN(val)) {
                total += val;
                count++;
              }
            }
            var avgElem = document.getElementById('avg-' + idx);
            if (count === 10) {
              avgElem.textContent = (total / count).toFixed(2);
            } else {
              avgElem.textContent = 'N/A';
            }
          }
        </script>
      </body>
    </html>
    """
    
    if request.method == 'POST':
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
    
    return render_template_string(feedback_template,
                                  department=department,
                                  semester=semester,
                                  mappings=mappings,
                                  questions=questions)

if __name__ == '__main__':
    # Create CSV files if they don't exist
    required_files = {
        DEPARTMENTS_FILE: ['department'],
        SEMESTERS_FILE: ['semester'],
        STAFFS_FILE: ['staff_name'],
        SUBJECTS_FILE: ['subject_name'],
        ADMIN_MAPPING_FILE: ['department', 'semester', 'staff', 'subject'],
        RATING_FILE: ['department', 'semester', 'staff', 'subject', 'average']
    }
    
    for file, headers in required_files.items():
        if not os.path.exists(file):
            with open(file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    app.run(debug=True)
