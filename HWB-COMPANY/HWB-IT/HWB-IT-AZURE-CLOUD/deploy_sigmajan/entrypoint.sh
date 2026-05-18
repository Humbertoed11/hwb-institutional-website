#!/bin/bash
echo "--- SigmaJan™ Force-Install Startup Sequence ---"
pip install --upgrade pip
pip install -r requirements.txt
echo "--- Starting Gunicorn ---"
gunicorn --bind 0.0.0.0:8000 app:app
