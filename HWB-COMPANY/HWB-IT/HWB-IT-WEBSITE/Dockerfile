# --- SigmaFidelity™ Institutional Dockerfile ---
# Standard: HWB-QMS-9.5 (System Containerization)
# Version: 1.0.0

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=main_app.py
ENV FLASK_ENV=production

# Install system dependencies for psycopg2 and high-fidelity computing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    postgresql-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pandas numpy

# Copy application code
COPY . .

# Create directory for logs if it doesn't exist
RUN mkdir -p /app/logs

# Expose institutional port
EXPOSE 5000

# Start the application using Gunicorn for commercial reliability
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main_app:app"]
# DEPLOY-FORCE: 1778957120
# WORKFLOW-RECOVERY: 2026-05-16_1345
# FORCE-DEPLOY-V3: 1778957400
# VERIFICATION-HEARTBEAT: 2026-05-16_1535
