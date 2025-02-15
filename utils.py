import csv
import os
from config import (
    RATING_FILE, STUDENT_FILE, ADMIN_MAPPING_FILE, 
    MAINRATING_FILE, REQUIRED_FILES
)

def read_csv_as_list(filename):
    """Return a list of values from the specified column in the CSV file."""
    if not os.path.exists(filename):
        return []
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        header = REQUIRED_FILES[filename][0]  # Get the expected header for this file
        return [row[header].strip() for row in reader if row.get(header)]

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
    """Return True if the student has already submitted feedback."""
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

def normalize_semester(semester):
    """Normalize semester string by removing 'semester' prefix if present."""
    semester = semester.strip()
    if semester.lower().startswith("semester"):
        semester = semester[len("semester"):].strip()
    return semester