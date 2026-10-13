# BUG-125: Gunicorn Single-Worker Jam & 30-Second Timeouts Slowing Password Reset Screen

## Problem
When a user requested a password reset link from the login page, the email arrived promptly via Microsoft Graph. However, upon clicking the reset link (`/reset-password/<token>`), the browser took over 60 seconds to render the "Set New Password" screen.

## Root Cause
1. **Single-Worker Bottleneck:** The web container (`hwb_web_app`) was executing Gunicorn with default single-process, single-threaded synchronous settings (`workers=1`, `threads=1`, `worker_class=sync`).
2. **Socket Read Blocking:** While automated background monitoring tools and terminal checks connected to port 5000, that single worker process became tied up in socket reads (`self.sock.recv`).
3. **Double 30-Second Restart Cycle:** With the single worker occupied, incoming browser requests were queued in the OS TCP backlog. Gunicorn logged two consecutive worker timeouts (`WORKER TIMEOUT (pid:7)` at 13:05:28 and `WORKER TIMEOUT (pid:17)` at 13:06:03), each waiting 30 seconds before killing the worker. Only after Worker 22 booted at 13:06:04 was the queue cleared, rendering the page at 13:06:08 (64 seconds total wait).

## Solution
1. **Multi-Threaded Worker Pool (`gthread`):**
   - Updated `docker-compose.yml` and `Dockerfile` to configure Gunicorn with:
     ```bash
     gunicorn --bind 0.0.0.0:5000 --workers 3 --threads 4 --worker-class gthread --timeout 120 --keep-alive 5 main_app:app
     ```
2. **Concurrent Lane Availability:**
   - 3 workers x 4 threads = 12 simultaneous request lanes.
   - Background pings and health checks consume only 1 thread out of 12, leaving 11 lanes completely open for instantaneous human user interactions.
3. **Empirical Verification:**
   - Parallel burst of 5 concurrent requests executed in 8ms to 170ms with 100% HTTP 200 OK responses.
   - Database connection pool verified healthy with 6.39ms latency.

## Prevention
Web application containers must always use multi-threaded worker configurations (`--worker-class gthread` with at least 3 workers and 4 threads) to prevent slow connections from freezing the platform for other users.
