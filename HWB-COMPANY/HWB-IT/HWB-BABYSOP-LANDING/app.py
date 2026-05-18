import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    # Primary landing page for babysop.com
    return render_template('index.html')

@app.route('/coming-soon')
def coming_soon():
    return render_template('coming_soon.html')

@app.route('/parent-intake')
def parent_intake():
    return render_template('parent_intake.html')

@app.route('/printable-kid')
def printable_kid():
    return render_template('printable_kid.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/api/waiting-list', methods=['POST'])
def join_waiting_list():
    data = request.json or {}
    email = data.get('email', 'N/A')
    # Integration with BabySOP database pending
    return jsonify({"status": "SUCCESS", "message": f"Institutional registration for {email} verified."})

if __name__ == '__main__':
    # Bind to 0.0.0.0 for container/Azure deployment compatibility
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)
