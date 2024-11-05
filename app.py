from flask import Flask, render_template, request
import PyPDF2
import os
import re

app = Flask(__name__)

def parse_clearpath_text(text, major_name):
    classes = {}
    lines = text.splitlines()
    current_major = major_name  # using the provided major name from the PDF filename without extension

    # skip the first two lines (assuming they are headers)
    lines = lines[2:]

    for line in lines:
        line = line.strip()
        if not line or "Completed" in line or "Graduation" in line or "Semester" in line or "Year" in line or "Institution" in line:
            continue

        # handle "or" scenarios (this includes electives or multiple course options)
        if " or " in line:
            or_pattern = r'([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)\s*or\s*([A-Z]{3,4} \d{4}): ([A-Za-z\s]+?)\s*(\d{1})?'
            or_matches = re.findall(or_pattern, line)

            for match in or_matches:
                course_id1, course_name1, course_id2, course_name2, credit_hours = match
                credit_hours = credit_hours.strip() if credit_hours else None

                if current_major not in classes:
                    classes[current_major] = []

                # append first course
                classes[current_major].append({'id': course_id1.strip(), 'name': course_name1.strip(), 'credit_hours': credit_hours})
                # append second course
                classes[current_major].append({'id': course_id2.strip(), 'name': course_name2.strip(), 'credit_hours': credit_hours})

            continue

        # handle general degree requirements or non-specific course descriptions without course id issue
        general_pattern = r'([A-Za-z\s]+(?:Elective|Humanities|Behavioral|Natural Science|Approved|Writing|Communication|Fine Arts|Global Citizenship)[\w\s,\'\-]*)\s*(?:\((.*)\))?'
        general_matches = re.findall(general_pattern, line)

        for match in general_matches:
            req_type, courses = match
            courses = courses.strip() if courses else None
            
            if current_major not in classes:
                classes[current_major] = []

            # store non-specific course requirements as a separate category
            classes[current_major].append({
                'id': None,  #no specific course ID
                'name': req_type.strip(),
                'credit_hours': courses  #store optional courses in the credit_hours field
            })

        #match regular course patterns based on CPEN 4700 or MATH 1950: Name CrsHours
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

#func for reading pdf and getting major name
def read_clearpath_pdf(file, major_name):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()

    return parse_clearpath_text(text, major_name)

# getting majors from clearpath folder so its data driven based on the pdfs
def load_majors_from_folder(folder_path):
    majors = []
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            major_name = filename[:-4]  #remove the '.pdf' extension for major name
            majors.append({'id': major_name.lower(), 'name': major_name.replace('_', ' ').title()})
    return majors

def load_clearpaths_from_folder(folder_path):
    all_classes = {}
    for filename in os.listdir(folder_path):
        if filename.endswith('.pdf'):
            major_name = filename[:-4]  #extract major from filename like before
            with open(os.path.join(folder_path, filename), 'rb') as file:
                clearpath_classes = read_clearpath_pdf(file, major_name)
                all_classes.update(clearpath_classes)
                print(f"Loaded classes from {filename}: {clearpath_classes}")  #print the recognized classes
    return all_classes

clearpaths_folder = 'C:\\Users\\Summer\\Desktop\\ai-advisor\\clearpaths'  #my fp
majors = load_majors_from_folder(clearpaths_folder)
classes = load_clearpaths_from_folder(clearpaths_folder)  #load classes at startup

@app.route('/')
def index():
    majors = load_majors_from_folder(clearpaths_folder)
    print(f"Loaded majors: {majors}")  #check loaded majors so can be in dropdown
    return render_template('index.html', majors=majors)

# can do app without uploading transcript dont worry on that for now
@app.route('/upload', methods=['POST'])
def upload_file():
    global classes
    if 'file' not in request.files:
        return "No file part"
    file = request.files['file']
    if file.filename == '':
        return "No selected file"
    
    #extract the major from the uploaded file's name
    major_name = file.filename[:-4]  
    with open(file, 'rb') as uploaded_file:
        #read and parse the uploaded ClearPath PDF and update the global classes dictionary
        clearpath_classes = read_clearpath_pdf(uploaded_file, major_name)
        classes.update(clearpath_classes)  #update global classes with new data
    
    #show success message and recognized classes
    message = "File uploaded and processed successfully."
    return render_template('index.html', majors=majors, classes=classes, message=message)

@app.route('/get_plan', methods=['GET', 'POST'])
def get_plan():
    if request.method == 'POST':
        major = request.form.get('major')
        print(f"Selected major: {major}")  # Debugging print can delete ltr

        major_classes = []

        #iterate over all classes to collect courses related to the selected major
        for key, value in classes.items():
            if key is None or major.lower() in key.lower():
                major_classes.extend(value)

        if major_classes:
            print(f"Classes available for {major}: {major_classes}")  # Debugging print
            return render_template('results.html', major=major, classes=major_classes)
        else:
            return render_template('results.html', major=major, classes=[], error="No plan available. Please pick a valid major.")
    
    #if it's a GET request, just render the major selection form
    return render_template('index.html')  # index.html is the page with the major selection form

from flask import Flask, render_template, request, redirect, url_for

@app.route('/schedule', methods=['POST'])
def schedule():
    major = request.form.get('major')
    if not major:
        #if major is not provided, redirect back to the form page or show an error
        return redirect(url_for('get_plan'))

    completed_courses = request.form.getlist('completed_courses')

    #get the list of all courses for the selected major
    major_classes = []
    for key, value in classes.items():
        if key and major.lower() in key.lower():  #ensure key is not None before checking
            major_classes.extend(value)

    #filter remaining courses
    remaining_courses = [course for course in major_classes if course['id'] not in completed_courses]

    #calculate progress percentage for progress of degree!!!!
    total_courses = len(major_classes)
    completed_count = total_courses - len(remaining_courses)
    progress_percentage = (completed_count / total_courses) * 100 if total_courses else 0

    return render_template('schedule.html', remaining_courses=remaining_courses, major=major, progress_percentage=int(progress_percentage))



if __name__ == '__main__':
    app.run(debug=True, port=5000)
