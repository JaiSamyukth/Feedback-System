import os
from flask import Flask
from routes.student_routes import student_bp
from routes.admin_routes import admin_bp
from routes.hod_routes import hod_bp
from config import REQUIRED_FILES
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure key in production

# Register blueprints
app.register_blueprint(student_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(hod_bp)

def create_required_files():
    """Create necessary CSV files if they don't exist."""
    for file, headers in REQUIRED_FILES.items():
        if not os.path.exists(file):
            with open(file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)

if __name__ == '__main__':
    create_required_files()
    app.run(debug=True)