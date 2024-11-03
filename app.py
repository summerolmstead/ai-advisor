from flask import Flask, render_template, request
import PyPDF2
import os
import re

app = Flask(__name__)

def load_majors_from_folder(folder_path):
    majors = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            major_name = filename[:-4]  # Remove the '.pdf' extension
            majors.append({'id': major_name.lower(), 'name': major_name.replace('_', ' ').title()})
    return majors

def read_clearpath_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return parse_clearpath_text(text)
'''
def parse_clearpath_text(text):
    classes = {}
    lines = text.splitlines()
    current_major = None

    # Skip the first two lines (assuming they are headers)
    lines = lines[2:]

    for line in lines:
        line = line.strip()
        if not line or "Completed" in line or "Graduation" in line:  # Skip empty lines and lines with specific text
            continue
        
        # Use regex to find courses in the line
        course_pattern = r'([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)(?=\s*\d{1,2})\s*(\d{1,2})?\s*'
        matches = re.findall(course_pattern, line)

        for match in matches:
            if match[0]:  # Check if the course ID exists
                course_id = match[0].strip()  # First captured group: Course ID
                course_name = match[1].strip()  # Second captured group: Course Name
                credit_hours = match[2].strip() if match[2] else None  # Third captured group: Credit Hours
                
                # Store the course details in the classes dictionary under the current major
                if current_major not in classes:
                    classes[current_major] = []
                classes[current_major].append({
                    'id': course_id,
                    'name': course_name,
                    'credit_hours': credit_hours
                })

        # Check if the line indicates a new major
        if ':' in line and not matches:  # This line does not have courses but might indicate a major
            parts = line.split(':')
            current_major = parts[0].strip()  # Update the current major

    return classes
'''

#handling or scenario 
import re

def parse_clearpath_text(text):
    classes = {}
    lines = text.splitlines()
    current_major = None

    # Skip the first two lines (assuming they are headers)
    lines = lines[2:]

    for line in lines:
        line = line.strip()
        if not line or "Completed" in line or "Graduation" in line:  # Skip empty lines and lines with specific text
            continue
        if not line or "Semester" in line or "Year" in line:  # Skip empty lines and lines with specific text
            continue

        # Check if the line indicates a new major
        if ':' in line and not re.search(r'\b[A-Z]{3,4} \d{4}\b', line):
            # If it contains a colon but doesn't have a course ID, treat it as a major
            parts = line.split(':')
            current_major = parts[0].strip()  # Update the current major
            continue

        # Check for " or " to identify scenarios with two courses
        if " or " in line:
            # Handle "or" scenarios
            or_pattern = r'([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)\s*or\s*([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)\s*(\d{1})\s*'
            or_matches = re.findall(or_pattern, line)

            for match in or_matches:
                if match[0]:  # Check if the first course ID exists
                    course_id1 = match[0].strip()  # First course ID
                    course_name1 = match[1].strip()  # First course Name
                    course_id2 = match[2].strip()  # Second course ID
                    course_name2 = match[3].strip()  # Second course Name
                    credit_hours = match[4].strip() if match[4] else None  # Credit Hours

                    # Store the first course details
                    if current_major not in classes:
                        classes[current_major] = []
                    classes[current_major].append({
                        'id': course_id1,
                        'name': f"{course_name1} (or {course_name2})",
                        'credit_hours': credit_hours
                    })

                    # Store the second course details
                    classes[current_major].append({
                        'id': course_id2,
                        'name': f"{course_name2} (or {course_name1})",
                        'credit_hours': credit_hours
                    })

            continue  # Skip to the next line after processing "or"

        # Use regex to find courses in the line that do not contain "or"
        course_pattern = r'([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)(?=\s*\d{1})\s*(\d{1})\s*'
        matches = re.findall(course_pattern, line)

        for match in matches:
            if match[0]:  # Check if the course ID exists
                course_id = match[0].strip()  # Course ID
                course_name = match[1].strip()  # Course Name
                credit_hours = match[2].strip() if match[2] else None  # Credit Hours

                # Store the course details in the classes dictionary under the current major
                if current_major not in classes:
                    classes[current_major] = []
                classes[current_major].append({
                    'id': course_id,
                    'name': course_name,
                    'credit_hours': credit_hours
                })

    return classes


def load_clearpaths_from_folder(folder_path):
    all_classes = {}
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            with open(os.path.join(folder_path, filename), 'rb') as file:
                clearpath_classes = read_clearpath_pdf(file)
                all_classes.update(clearpath_classes)
                print(f"Loaded classes from {filename}: {clearpath_classes}")  # Print the recognized classes
    return all_classes


# Update this path to your actual clearpaths directory
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
    
    # Read the ClearPath PDF and update the classes dictionary
    classes = load_clearpaths_from_folder(clearpaths_folder)
    
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)