"""
SigmaFidelity™ Enterprise Rate Limiting & Abuse Defense Engine
Standard: HWB-QMS-7.6 Enterprise Architecture Standards (SOC 2 / ISO 27001)
Custodians: George (Systems Architect) & Humberto Dominguez (CEO)
"""

import time
import threading
from functools import wraps
from flask import request, jsonify, render_template_string, Response

class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Guarantees strict throughput governance across web endpoints.
    """
    def __init__(self):
        self._requests = {}
        self._lock = threading.Lock()
        self._whitelist = {'127.0.0.1', '::1', 'localhost'}

    def is_allowed(self, key: str, limit: int, period_seconds: int) -> tuple[bool, int]:
        """
        Evaluates whether a request from the given key is within quota.
        Returns: (is_allowed: bool, retry_after_seconds: int)
        """
        now = time.time()
        window_start = now - period_seconds

        with self._lock:
            if key not in self._requests:
                self._requests[key] = []

            # Prune timestamps older than window
            self._requests[key] = [t for t in self._requests[key] if t > window_start]

            if len(self._requests[key]) < limit:
                self._requests[key].append(now)
                return True, 0

            # Quota exceeded; calculate wait time
            oldest_relevant = self._requests[key][0]
            retry_after = max(1, int(oldest_relevant + period_seconds - now))
            return False, retry_after

    def clear(self):
        """Clears all stored rate limit history."""
        with self._lock:
            self._requests.clear()


limiter = SlidingWindowRateLimiter()


def get_client_ip() -> str:
    """Extracts client IP, respecting proxy forwarding headers."""
    if request.headers.get('X-Forwarded-For'):
        return request.headers['X-Forwarded-For'].split(',')[0].strip()
    return request.remote_addr or 'unknown'


def rate_limit(limit: int = 5, period_seconds: int = 60, scope: str = None):
    """
    Enterprise rate limiting decorator.
    Applies sliding window rate limits per client IP address.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = get_client_ip()
            key = f"{scope or f.__name__}:{ip}"
            
            allowed, retry_after = limiter.is_allowed(key, limit, period_seconds)
            if not allowed:
                print(f"[SECURITY_ALERT] Rate limit exceeded for {key} ({limit}/{period_seconds}s). Blocked for {retry_after}s.", flush=True)
                
                # Format response based on request content negotiation
                is_json = request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/')
                if is_json:
                    resp = jsonify({
                        'status': 'error',
                        'error': 'Too Many Requests',
                        'message': f'Rate limit exceeded. Please wait {retry_after} seconds before retrying.',
                        'retry_after': retry_after
                    })
                    resp.status_code = 429
                    resp.headers['Retry-After'] = str(retry_after)
                    return resp
                
                # HTML presentation for web form submissions
                html_msg = f"""
                <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 500px; margin: 60px auto; padding: 30px; border: 1px solid #e2e8f0; border-radius: 8px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    <h2 style="color: #dc2626; margin-top: 0;">Too Many Requests</h2>
                    <p style="color: #475569; line-height: 1.6;">Our security defenses detected high activity from your address. For protection against automated attacks, please wait <strong>{retry_after} seconds</strong> before trying again.</p>
                    <a href="javascript:history.back()" style="display: inline-block; margin-top: 15px; padding: 8px 16px; background-color: #2563eb; color: white; border-radius: 6px; text-decoration: none; font-weight: 500;">Go Back</a>
                </div>
                """
                resp = Response(html_msg, status=429, mimetype='text/html')
                resp.headers['Retry-After'] = str(retry_after)
                return resp

            return f(*args, **kwargs)
        return decorated_function
    return decorator
