from flask import Flask, render_template, request
import PyPDF2
import os
import re

app = Flask(__name__)


"""def parse_clearpath_text(text, major_name):
    classes = {}
    lines = text.splitlines()
    current_major = major_name  # Use the provided major name from the PDF filename

    # Skip the first two lines (assuming they are headers)
    lines = lines[2:]

    for line in lines:
        line = line.strip()
        if not line or "Completed" in line or "Graduation" in line or "Semester" in line or "Year" in line:
            continue

        # Handle "or" scenarios
        if " or " in line:
            or_pattern = r'([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)\s*or\s*([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)\s*(\d{1})?'
            or_matches = re.findall(or_pattern, line)

            for match in or_matches:
                course_id1, course_name1, course_id2, course_name2, credit_hours = match
                credit_hours = credit_hours.strip() if credit_hours else None

                if current_major not in classes:
                    classes[current_major] = []

                # Append first course
                classes[current_major].append({'id': course_id1.strip(), 'name': course_name1.strip(), 'credit_hours': credit_hours})
                # Append second course
                classes[current_major].append({'id': course_id2.strip(), 'name': course_name2.strip(), 'credit_hours': credit_hours})

            continue

        # Match regular course patterns (Updated regex)
        # We allow the course name to include multiple words and spaces until a possible credit hour is encountered
        course_pattern = r'([A-Z]{3,4} \d{4}): ([A-Za-z\s,\'\-]+)\s*(\d{1,2})?\s*'
        matches = re.findall(course_pattern, line)

        for match in matches:
            course_id, course_name, credit_hours = match
            credit_hours = credit_hours.strip() if credit_hours else None
            
            if current_major not in classes:
                classes[current_major] = []
            if not any(c['id'] == course_id for c in classes[current_major]):  # Avoid duplicates
                classes[current_major].append({'id': course_id.strip(), 'name': course_name.strip(), 'credit_hours': credit_hours})

    return {current_major: classes[current_major]} if current_major else {}"""

def parse_clearpath_text(text, major_name):
    classes = {}
    lines = text.splitlines()
    current_major = major_name  # Use the provided major name from the PDF filename

    # Skip the first two lines (assuming they are headers)
    lines = lines[2:]

    for line in lines:
        line = line.strip()
        if not line or "Completed" in line or "Graduation" in line or "Semester" in line or "Year" in line or "Institution" in line:
            continue

        # Handle "or" scenarios (this includes electives or multiple course options)
        if " or " in line:
            or_pattern = r'([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)\s*or\s*([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)\s*(\d{1})?'
            or_matches = re.findall(or_pattern, line)

            for match in or_matches:
                course_id1, course_name1, course_id2, course_name2, credit_hours = match
                credit_hours = credit_hours.strip() if credit_hours else None

                if current_major not in classes:
                    classes[current_major] = []

                # Append first course
                classes[current_major].append({'id': course_id1.strip(), 'name': course_name1.strip(), 'credit_hours': credit_hours})
                # Append second course
                classes[current_major].append({'id': course_id2.strip(), 'name': course_name2.strip(), 'credit_hours': credit_hours})

            continue

        # Handle general degree requirements or non-specific course descriptions
        general_pattern = r'([A-Za-z\s]+(?:Elective|Humanities|Behavioral|Natural Science|Approved|Writing|Communication|Fine Arts|Global Citizenship)[\w\s,\'\-]*)\s*(?:\((.*)\))?'
        general_matches = re.findall(general_pattern, line)

        for match in general_matches:
            req_type, courses = match
            courses = courses.strip() if courses else None
            
            if current_major not in classes:
                classes[current_major] = []

            # Store non-specific course requirements as a separate category
            classes[current_major].append({
                'id': None,  # No specific course ID
                'name': req_type.strip(),
                'credit_hours': courses  # Store optional courses in the credit_hours field
            })

        # Match regular course patterns (Updated regex)
        course_pattern = r'([A-Z]{3,4} \d{4}): ([A-Za-z\s,\'\-]+)\s*(\d{1,2})?\s*'
        matches = re.findall(course_pattern, line)

        for match in matches:
            course_id, course_name, credit_hours = match
            credit_hours = credit_hours.strip() if credit_hours else None
            
            if current_major not in classes:
                classes[current_major] = []
            if not any(c['id'] == course_id for c in classes[current_major]):  # Avoid duplicates
                classes[current_major].append({'id': course_id.strip(), 'name': course_name.strip(), 'credit_hours': credit_hours})

    return {current_major: classes[current_major]} if current_major else {}


def read_clearpath_pdf(file, major_name):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    return parse_clearpath_text(text, major_name)

def load_majors_from_folder(folder_path):
    majors = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            major_name = filename[:-4]  # Remove the '.pdf' extension
            majors.append({'id': major_name.lower(), 'name': major_name.replace('_', ' ').title()})
    return majors

def load_clearpaths_from_folder(folder_path):
    all_classes = {}
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            major_name = filename[:-4]  # Extract major from filename
            with open(os.path.join(folder_path, filename), 'rb') as file:
                clearpath_classes = read_clearpath_pdf(file, major_name)
                all_classes.update(clearpath_classes)
                print(f"Loaded classes from {filename}: {clearpath_classes}")  # Print the recognized classes
    return all_classes

clearpaths_folder = 'C:\\Users\\Summer\\Desktop\\ai-advisor\\clearpaths'  # Change as needed
majors = load_majors_from_folder(clearpaths_folder)
classes = load_clearpaths_from_folder(clearpaths_folder)  # Load classes at startup

@app.route('/')
def index():
    majors = load_majors_from_folder(clearpaths_folder)
    print(f"Loaded majors: {majors}")  # Check loaded majors
    return render_template('index.html', majors=majors)

@app.route('/upload', methods=['POST'])
def upload_file():
    global classes
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    
    # Extract the major from the uploaded file's name
    major_name = file.filename[:-4]  # Remove the '.pdf' extension
    with open(file, 'rb') as uploaded_file:
        # Read and parse the uploaded ClearPath PDF and update the global classes dictionary
        clearpath_classes = read_clearpath_pdf(uploaded_file, major_name)
        classes.update(clearpath_classes)  # Update global classes with new data
    
    # Show success message and recognized classes
    message = "File uploaded and processed successfully."
    return render_template('index.html', majors=majors, classes=classes, message=message)

@app.route('/get_plan', methods=['POST'])
def get_plan():
    major = request.form.get('major')
    print(f"Selected major: {major}")  # Debugging print

    major_classes = []

    # Iterate over all classes to collect courses related to the selected major
    for key, value in classes.items():
        if key is None or major.lower() in key.lower():
            major_classes.extend(value)

    if major_classes:
        print(f"Classes available for {major}: {major_classes}")  # Debugging print
        return render_template('results.html', major=major, classes=major_classes)
    else:
        return render_template('results.html', major=major, classes=[], error="No plan available. Please pick a valid major.")

from flask import Flask, render_template, request, redirect, url_for

@app.route('/schedule', methods=['POST'])
def schedule():
    completed_courses = request.form.getlist('completed_courses')  # Get the list of completed courses from the form

    remaining_courses = []
    for course in classes.get(major, []):  # Get the list of courses for the selected major
        if course['id'] not in completed_courses:
            remaining_courses.append(course)  # If the course wasn't completed, add to remaining courses

    return render_template('schedule.html', remaining_courses=remaining_courses, major=major)



if __name__ == '__main__':
    app.run(debug=True, port=5000)
