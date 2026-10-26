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
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir pandas numpy

# Copy application code
COPY . .

# Create unprivileged application user and writable runtime directories (CIS Docker Benchmark 4.1)
RUN groupadd -g 1000 hwbapp && \
    useradd -m -u 1000 -g hwbapp -s /usr/sbin/nologin hwbapp && \
    mkdir -p /app/logs /app/vault/hr_documents && \
    chown -R hwbapp:hwbapp /app

USER hwbapp

# Expose institutional port
EXPOSE 5000

# Start the application using Gunicorn for commercial reliability (HWB-QMS-11.14: preloaded right-sized workers)
CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "8", "--worker-class", "gthread", "--timeout", "45", "--keep-alive", "65", "--max-requests", "10000", "--max-requests-jitter", "500", "main_app:app"]
