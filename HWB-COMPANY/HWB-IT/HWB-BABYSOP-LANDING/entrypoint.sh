#!/bin/bash
echo "--- BabySOP Landing Startup Sequence ---"
pip install -r requirements.txt
echo "--- Executing Startup Database Sync ---"
python3 scripts/hex_sync.py
python3 scripts/HEX-PERSISTENCE-PROTOCOL.py
echo "--- Starting Gunicorn ---"
gunicorn --bind 0.0.0.0:8000 --timeout 600 app:app
