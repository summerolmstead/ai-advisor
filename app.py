from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    
   return render_template('index.html')
   #return "Hello!!!!"

@app.route('/get_plan', methods=['POST'])
def get_plan():
    major = request.form.get('major')
    return render_template('results.html', major=major)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
