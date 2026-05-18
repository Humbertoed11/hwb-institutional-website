import os
from flask import Flask, render_template
from main_app import app

# Setup a test request context to handle url_for
with app.test_request_context():
    try:
        print("Attempting to render HWB-WEB Resources.html with request context...")
        html = render_template('HWB-WEB Resources.html')
        print("SUCCESS: Template rendered without Internal Server Error.")
    except Exception as e:
        print(f"CRITICAL ERROR during render: {str(e)}")
        import traceback
        traceback.print_exc()
